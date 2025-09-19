import { Controller, Get, Inject } from '@nestjs/common';
import { AppService } from './app.service';
import { TRANSCRIBE_CLIENT } from './common/lib/constnts/constants';
import { ClientProxy } from '@nestjs/microservices';
import { firstValueFrom } from 'rxjs';

@Controller()
export class AppController {
  constructor(
    private readonly appService: AppService,
    @Inject(TRANSCRIBE_CLIENT) private readonly transcribeClient: ClientProxy,
  ) {}

  @Get()
  getHello(): string {
    return this.appService.getHello();
  }

  @Get('transcribe/health')
  healthTranscribe() {
    return firstValueFrom(
      this.transcribeClient.send('health_check', { message: 'check' }),
    );
  }
}
