import { Module } from '@nestjs/common';
import { ClientsModule, Transport } from '@nestjs/microservices';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { PlatformSettingsService } from '@podium/shared';
import { EventsController } from './events.controller';
import { EventsService } from './events.service';

@Module({
  imports: [
    ClientsModule.registerAsync([
      {
        name: 'KAFKA_SERVICE',
        imports: [ConfigModule],
        inject: [ConfigService],
        useFactory: (config: ConfigService) => ({
          transport: Transport.KAFKA,
          options: {
            client: {
              clientId: 'events-service-producer',
              brokers: [config.get<string>('KAFKA_BROKER', 'localhost:9092')!],
            },
            producer: {
              allowAutoTopicCreation: true,
            },
          },
        }),
      },
    ]),
  ],
  controllers: [EventsController],
  providers: [EventsService, PlatformSettingsService],
  exports: [EventsService],
})
export class EventsModule {}
