import { Injectable, ExecutionContext } from '@nestjs/common';
import { AuthGuard } from '@nestjs/passport';

/**
 * Like JwtAuthGuard, but does not reject unauthenticated requests.
 * If a valid Bearer token is present, `request.user` is populated.
 * Otherwise, `request.user` remains undefined and the request proceeds.
 */
@Injectable()
export class OptionalJwtAuthGuard extends AuthGuard('jwt') {
  canActivate(context: ExecutionContext) {
    return super.canActivate(context);
  }

  handleRequest(_err: any, user: any) {
    // Don't throw on missing/invalid token — just return null
    return user || null;
  }
}
