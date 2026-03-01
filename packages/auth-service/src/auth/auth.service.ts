import { Injectable, Inject, HttpException, HttpStatus } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { JwtService } from '@nestjs/jwt';
import { randomInt } from 'crypto';
import { eq, lt } from 'drizzle-orm';
import { SESClient, SendEmailCommand } from '@aws-sdk/client-ses';
import { DRIZZLE_RW, type Database, adminOtps } from '@podium/shared';
import { magicLinkHtml, adminOtpHtml } from '../emails/templates';

@Injectable()
export class AuthService {
  private readonly secret: string;
  private readonly algorithm: string;
  private readonly accessTokenExpireMinutes: number;
  private readonly magicLinkExpireMinutes = 15;
  private readonly productionUrl: string;
  private readonly sesFromEmail: string;
  private readonly sesClient: SESClient | null;

  private readonly OTP_TTL_MS = 5 * 60 * 1000; // 5 minutes

  constructor(
    private readonly jwtService: JwtService,
    private readonly config: ConfigService,
    @Inject(DRIZZLE_RW) private readonly dbRw: Database,
  ) {
    this.secret = config.get<string>('PODIUM_JWT_SECRET')!;
    this.algorithm = config.get<string>('PODIUM_JWT_ALGORITHM', 'HS256')!;
    this.accessTokenExpireMinutes = config.get<number>(
      'PODIUM_JWT_EXPIRE_MINUTES',
      2880,
    )!;
    this.productionUrl = config.get<string>(
      'PODIUM_PRODUCTION_URL',
      'http://localhost:3000',
    )!;
    this.sesFromEmail = config.get<string>('SES_FROM_EMAIL', '')!;

    const awsRegion = config.get<string>('AWS_REGION', '');
    const awsKeyId = config.get<string>('AWS_ACCESS_KEY_ID', '');
    const awsSecret = config.get<string>('AWS_SECRET_ACCESS_KEY', '');

    if (awsRegion && awsKeyId && awsSecret && this.sesFromEmail) {
      this.sesClient = new SESClient({
        region: awsRegion,
        credentials: {
          accessKeyId: awsKeyId,
          secretAccessKey: awsSecret,
        },
      });
    } else {
      this.sesClient = null;
    }
  }

  createAccessToken(
    email: string,
    expiresInMinutes: number,
    tokenType: string,
  ): string {
    return this.jwtService.sign(
      { sub: email, token_type: tokenType },
      { expiresIn: `${expiresInMinutes}m` },
    );
  }

  private async sendEmail(
    to: string,
    subject: string,
    htmlBody: string,
    textBody: string,
  ): Promise<void> {
    if (!this.sesClient) {
      console.log('[WARNING] SES not configured. Email not sent.');
      return;
    }

    try {
      await this.sesClient.send(
        new SendEmailCommand({
          Source: this.sesFromEmail,
          Destination: { ToAddresses: [to] },
          Message: {
            Subject: { Data: subject, Charset: 'UTF-8' },
            Body: {
              Html: { Data: htmlBody, Charset: 'UTF-8' },
              Text: { Data: textBody, Charset: 'UTF-8' },
            },
          },
        }),
      );
    } catch (err: any) {
      console.error('[SES] Failed to send email:', err?.message);
      throw new HttpException(
        'Failed to send auth email',
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  async sendMagicLink(email: string, redirect: string): Promise<void> {
    const token = this.createAccessToken(
      email,
      this.magicLinkExpireMinutes,
      'magic_link',
    );

    let magicLink: string;
    if (redirect) {
      magicLink = `${this.productionUrl}/${encodeURIComponent(redirect)}?token=${token}`;
    } else {
      magicLink = `${this.productionUrl}?token=${token}`;
    }

    console.log(`Magic link for ${email}: ${magicLink}`);

    const htmlBody = magicLinkHtml.replaceAll('{{MAGIC_LINK}}', magicLink);

    await this.sendEmail(
      email,
      'Your Podium magic link',
      htmlBody,
      `Sign in to Podium:\n\n${magicLink}\n\nThis link expires in 15 minutes.`,
    );
  }

  verifyMagicLinkToken(token: string): { email: string; tokenType: string } {
    try {
      const payload = this.jwtService.verify(token);
      const email = payload.sub as string | undefined;
      const tokenType = payload.token_type as string | undefined;
      if (!email || tokenType !== 'magic_link') {
        throw new HttpException('Invalid token', HttpStatus.BAD_REQUEST);
      }
      return { email, tokenType };
    } catch (err) {
      if (err instanceof HttpException) throw err;
      throw new HttpException('Invalid token', HttpStatus.BAD_REQUEST);
    }
  }

  createUserAccessToken(email: string): string {
    return this.createAccessToken(
      email,
      this.accessTokenExpireMinutes,
      'access',
    );
  }

  // ── Admin OTP ────────────────────────────────────────────────────────

  async sendOtpEmail(email: string, code: string): Promise<void> {
    console.log(`Admin OTP for ${email}: ${code}`);

    const htmlBody = adminOtpHtml.replaceAll('{{OTP_CODE}}', code);

    await this.sendEmail(
      email,
      `Your Podium admin code: ${code}`,
      htmlBody,
      `Your Podium admin login code is: ${code}\n\nIt expires in 5 minutes.`,
    );
  }

  async generateOtp(email: string): Promise<string> {
    const now = Date.now();

    // Clean up expired OTPs (fire-and-forget, non-blocking)
    this.dbRw.delete(adminOtps).where(lt(adminOtps.expires_at, now)).catch(() => {});

    // Generate cryptographically random 6-digit code
    const code = String(randomInt(100000, 999999));

    await this.dbRw
      .insert(adminOtps)
      .values({ email, code, expires_at: now + this.OTP_TTL_MS })
      .onConflictDoUpdate({
        target: adminOtps.email,
        set: { code, expires_at: now + this.OTP_TTL_MS },
      });

    return code;
  }

  async verifyOtp(email: string, code: string): Promise<boolean> {
    const entry = await this.dbRw.query.adminOtps.findFirst({
      where: eq(adminOtps.email, email),
    });
    if (!entry) return false;

    if (entry.expires_at < Date.now()) {
      await this.dbRw.delete(adminOtps).where(eq(adminOtps.email, email));
      return false;
    }

    if (entry.code !== code) return false;

    // OTP is single-use
    await this.dbRw.delete(adminOtps).where(eq(adminOtps.email, email));
    return true;
  }
}
