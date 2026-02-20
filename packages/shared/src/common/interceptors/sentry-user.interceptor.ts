import {
  Injectable,
  NestInterceptor,
  ExecutionContext,
  CallHandler,
} from '@nestjs/common';
import { Observable } from 'rxjs';
import * as Sentry from '@sentry/nestjs';

@Injectable()
export class SentryUserInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    const request = context.switchToHttp().getRequest();
    const auth = request.headers?.authorization ?? '';

    if (auth.startsWith('Bearer ')) {
      try {
        const payload = JSON.parse(
          Buffer.from(auth.split('.')[1], 'base64').toString(),
        );
        const email = payload?.sub;
        if (email && email.includes('@')) {
          Sentry.setUser({ email });
        } else {
          Sentry.setUser({ ip_address: request.ip });
        }
      } catch {
        Sentry.setUser({ ip_address: request.ip });
      }
    } else {
      Sentry.setUser({ ip_address: request.ip });
    }

    return next.handle();
  }
}
