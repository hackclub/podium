import { Module } from '@nestjs/common';
import { VoteConsumer } from './vote.consumer';

@Module({
  controllers: [VoteConsumer],
})
export class VotesModule {}
