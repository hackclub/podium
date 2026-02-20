import {
  UnauthorizedException,
  ForbiddenException,
} from '@nestjs/common';

export const BAD_AUTH = new UnauthorizedException(
  'Invalid authentication credentials',
);
export const BAD_ACCESS = new ForbiddenException(
  "You don't have permission to do this",
);
