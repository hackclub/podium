import 'reflect-metadata';
import { NestFactory } from '@nestjs/core';
import { ValidationPipe } from '@nestjs/common';
import { MicroserviceOptions, Transport } from '@nestjs/microservices';
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

  const kafkaBroker = process.env.KAFKA_BROKER || 'localhost:9092';

  app.connectMicroservice<MicroserviceOptions>({
    transport: Transport.KAFKA,
    options: {
      client: {
        clientId: 'events-service',
        brokers: [kafkaBroker],
      },
      consumer: {
        groupId: 'events-service-votes',
        sessionTimeout: 30000,
      },
    },
  });

  await app.startAllMicroservices();

  const port = process.env.PORT || 8002;
  await app.listen(port);
  console.log(`Events service listening on port ${port}`);
  console.log(`Kafka consumer connected to ${kafkaBroker}`);
}
bootstrap();
