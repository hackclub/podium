import {
  Controller,
  Post,
  Get,
  Body,
  Query,
  Req,
  Inject,
  Logger,
  HttpException,
  HttpStatus,
} from '@nestjs/common';
import { type Request } from 'express';
import { IsEmail, IsString } from 'class-validator';
import { eq, or } from 'drizzle-orm';
import { DRIZZLE_RW, type Database, users, events, RateLimit } from '@podium/shared';
import { AuthService } from './auth.service';

class UserLoginPayload {
  @IsEmail()
  email!: string;
}

class AdminOtpRequestPayload {
  @IsEmail()
  email!: string;
}

class AdminOtpVerifyPayload {
  @IsEmail()
  email!: string;

  @IsString()
  code!: string;
}

@Controller('auth')
export class AuthController {
  private readonly logger = new Logger(AuthController.name);

  constructor(
    private readonly authService: AuthService,
    @Inject(DRIZZLE_RW) private readonly db: Database,
  ) {}

  @Post('request-login')
  @RateLimit(1000, 60)
  async requestLogin(
    @Body() body: UserLoginPayload,
    @Query('redirect') redirect: string = '',
  ) {
    const email = body.email.trim().toLowerCase();
    const existing = await this.db.query.users.findFirst({
      where: eq(users.email, email),
    });
    if (!existing) {
      throw new HttpException('User not found', HttpStatus.NOT_FOUND);
    }
    await this.authService.sendMagicLink(email, redirect);
  }

  @Get('verify')
  @RateLimit(1000, 60)
  async verifyToken(@Query('token') token: string) {
    const { email } = this.authService.verifyMagicLinkToken(token);

    const user = await this.db.query.users.findFirst({
      where: eq(users.email, email),
    });
    if (!user) {
      throw new HttpException('User not found', HttpStatus.NOT_FOUND);
    }

    const accessToken = this.authService.createUserAccessToken(email);
    return {
      access_token: accessToken,
      token_type: 'access',
      user: {
        id: user.id,
        display_name: user.display_name,
        email: user.email,
        first_name: user.first_name,
        last_name: user.last_name,
      },
    };
  }

  // ── Admin OTP ────────────────────────────────────────────────────────

  /** Check if user has any admin-level access (is_admin, superadmin, event owner, POC, or RM) */
  private async hasAdminAccess(userId: string, isAdmin: boolean): Promise<boolean> {
    if (isAdmin) return true;
    const event = await this.db.query.events.findFirst({
      where: or(
        eq(events.owner_id, userId),
        eq(events.poc_id, userId),
        eq(events.rm_id, userId),
      ),
    });
    return !!event;
  }

  @Post('admin/request-otp')
  @RateLimit(50, 60)
  async requestAdminOtp(
    @Body() body: AdminOtpRequestPayload,
    @Req() req: Request,
  ) {
    const email = body.email.trim().toLowerCase();
    const ip = req.headers['x-forwarded-for']
      ? String(req.headers['x-forwarded-for']).split(',')[0].trim()
      : req.ip;
    this.logger.debug(`Admin OTP requested for ${email} from IP ${ip}`);

    const user = await this.db.query.users.findFirst({
      where: eq(users.email, email),
    });
    if (!user || !(await this.hasAdminAccess(user.id, user.is_admin))) {
      // Return same response whether user exists or not (prevent enumeration)
      return { message: 'If that email is an admin account, a code has been generated' };
    }

    const code = await this.authService.generateOtp(email);

    console.log(`Admin OTP for ${email}: ${code}`);
    await this.authService.sendOtpEmail(email, code);

    return { message: 'If that email is an admin account, a code has been generated' };
  }

  @Post('admin/verify-otp')
  @RateLimit(100, 60)
  async verifyAdminOtp(@Body() body: AdminOtpVerifyPayload) {
    const email = body.email.trim().toLowerCase();
    const code = body.code.trim();

    const user = await this.db.query.users.findFirst({
      where: eq(users.email, email),
    });
    if (!user || !(await this.hasAdminAccess(user.id, user.is_admin))) {
      throw new HttpException('Invalid code', HttpStatus.UNAUTHORIZED);
    }

    const valid = await this.authService.verifyOtp(email, code);
    if (!valid) {
      throw new HttpException('Invalid or expired code', HttpStatus.UNAUTHORIZED);
    }

    const accessToken = this.authService.createUserAccessToken(email);
    return {
      access_token: accessToken,
      token_type: 'access',
      user: {
        id: user.id,
        email: user.email,
        display_name: user.display_name,
        first_name: user.first_name,
        is_admin: user.is_admin,
      },
    };
  }
}
