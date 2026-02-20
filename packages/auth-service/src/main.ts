import 'reflect-metadata';
import { NestFactory } from '@nestjs/core';
import { ValidationPipe } from '@nestjs/common';
import * as Sentry from '@sentry/nestjs';
import { eq } from 'drizzle-orm';
import { DRIZZLE, type Database, users } from '@podium/shared';
import { AppModule } from './app.module';

async function bootstrap() {
  if (process.env.NODE_ENV !== 'development') {
    Sentry.init({
      dsn: 'https://489f4a109d07aeadfd13387bcd3197ab@o4508979744210944.ingest.de.sentry.io/4508979747553360',
      tracesSampleRate: 0, // Datadog APM handles tracing; keep Sentry for errors only
      sendDefaultPii: true,
    });
  }

  const app = await NestFactory.create(AppModule);
  app.getHttpAdapter().getInstance().set('trust proxy', 1);
  app.setGlobalPrefix('api');
  app.enableCors({ origin: '*', credentials: true });
  app.useGlobalPipes(
    new ValidationPipe({ whitelist: true, transform: true }),
  );

  // Ensure default admin exists
  try {
    const db = app.get<Database>(DRIZZLE);
    const adminEmail = 'sebastian@hackclub.com';
    const existing = await db.query.users.findFirst({
      where: eq(users.email, adminEmail),
    });
    if (!existing) {
      await db.insert(users).values({
        email: adminEmail,
        first_name: 'Sebastian',
        last_name: '',
        display_name: 'Sebastian',
        is_admin: true,
        phone: '',
        street_1: '',
        street_2: '',
        city: '',
        state: '',
        zip_code: '',
        country: '',
      });
      console.log(`Created default admin: ${adminEmail}`);
    } else if (!existing.is_admin) {
      await db
        .update(users)
        .set({ is_admin: true })
        .where(eq(users.email, adminEmail));
      console.log(`Promoted existing user to admin: ${adminEmail}`);
    }
  } catch (err) {
    console.error('Failed to seed default admin:', err);
  }

  const port = process.env.PORT || 8001;
  await app.listen(port);
  console.log(`Auth service listening on port ${port}`);
}
bootstrap();
