import 'reflect-metadata';
import { NestFactory } from '@nestjs/core';
import { ValidationPipe } from '@nestjs/common';
import * as Sentry from '@sentry/nestjs';
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

  const port = process.env.PORT || 8003;
  await app.listen(port);
  console.log(`Projects service listening on port ${port}`);
}
bootstrap();
