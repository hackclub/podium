import {
  Controller,
  Get,
  Post,
  Put,
  Body,
  Param,
  Query,
  UseGuards,
  HttpException,
  HttpStatus,
} from '@nestjs/common';
import { User, JwtAuthGuard, CurrentUser } from '@podium/shared';
import { UsersService } from './users.service';
import {
  IsEmail,
  IsOptional,
  IsString,
  IsDateString,
} from 'class-validator';

class CreateUserDto {
  @IsEmail()
  email!: string;

  @IsString()
  first_name!: string;

  @IsOptional()
  @IsString()
  last_name?: string;

  @IsOptional()
  @IsString()
  display_name?: string;

  @IsOptional()
  @IsString()
  phone?: string;

  @IsOptional()
  @IsString()
  street_1?: string;

  @IsOptional()
  @IsString()
  street_2?: string;

  @IsOptional()
  @IsString()
  city?: string;

  @IsOptional()
  @IsString()
  state?: string;

  @IsOptional()
  @IsString()
  zip_code?: string;

  @IsOptional()
  @IsString()
  country?: string;

  @IsOptional()
  @IsDateString()
  dob?: string;
}

class UpdateUserDto {
  @IsOptional()
  @IsString()
  display_name?: string;

  @IsOptional()
  @IsString()
  first_name?: string;

  @IsOptional()
  @IsString()
  last_name?: string;

  @IsOptional()
  @IsString()
  phone?: string;

  @IsOptional()
  @IsString()
  street_1?: string;

  @IsOptional()
  @IsString()
  street_2?: string;

  @IsOptional()
  @IsString()
  city?: string;

  @IsOptional()
  @IsString()
  state?: string;

  @IsOptional()
  @IsString()
  zip_code?: string;

  @IsOptional()
  @IsString()
  country?: string;

  @IsOptional()
  @IsDateString()
  dob?: string;
}

@Controller('users')
export class UsersController {
  constructor(private readonly usersService: UsersService) {}

  @Get('exists')
  async userExists(@Query('email') email: string) {
    const emailLower = email?.trim().toLowerCase();
    if (!emailLower) {
      return { exists: false };
    }
    const user = await this.usersService.findByEmail(emailLower);
    return { exists: !!user };
  }

  @Get('lookup')
  @UseGuards(JwtAuthGuard)
  async lookupTeammate(@Query('email') email: string) {
    const emailLower = email?.trim().toLowerCase();
    if (!emailLower) {
      throw new HttpException('Email is required', HttpStatus.BAD_REQUEST);
    }

    const user = await this.usersService.findByEmail(emailLower);

    // Never return PII — only which fields are missing
    const allFields = [
      'first_name', 'last_name', 'phone',
      'street_1', 'city', 'state', 'zip_code', 'country', 'dob',
    ] as const;

    if (!user) {
      return { found: false, missing_fields: [...allFields] };
    }

    const missing: string[] = [];
    if (!user.first_name) missing.push('first_name');
    if (!user.last_name) missing.push('last_name');
    if (!user.phone) missing.push('phone');
    if (!user.street_1) missing.push('street_1');
    if (!user.city) missing.push('city');
    if (!user.state) missing.push('state');
    if (!user.zip_code) missing.push('zip_code');
    if (!user.country) missing.push('country');
    if (!user.dob) missing.push('dob');

    return { found: true, missing_fields: missing };
  }

  @Get('current')
  @UseGuards(JwtAuthGuard)
  async getCurrentUser(@CurrentUser() user: User) {
    const fullUser = await this.usersService.findById(user.id);
    return {
      id: user.id,
      display_name: user.display_name,
      email: user.email,
      first_name: user.first_name,
      last_name: user.last_name,
      is_admin: user.is_admin,
      is_superadmin: user.is_superadmin,
      has_address: !!(fullUser?.street_1 && fullUser?.city && fullUser?.state && fullUser?.zip_code && fullUser?.country),
      has_dob: !!fullUser?.dob,
      has_phone: !!fullUser?.phone,
    };
  }

  @Put('current')
  @UseGuards(JwtAuthGuard)
  async updateCurrentUser(
    @CurrentUser() user: User,
    @Body() body: UpdateUserDto,
  ) {
    const updated = await this.usersService.updateUser(user, body);
    return {
      id: updated.id,
      display_name: updated.display_name,
      email: updated.email,
      first_name: updated.first_name,
      last_name: updated.last_name,
      has_address: !!(updated.street_1 && updated.city && updated.state && updated.zip_code && updated.country),
      has_dob: !!updated.dob,
      has_phone: !!updated.phone,
    };
  }

  @Get(':user_id')
  async getUserPublic(@Param('user_id') userId: string) {
    const user = await this.usersService.findById(userId);
    if (!user) {
      throw new HttpException('User not found', HttpStatus.NOT_FOUND);
    }
    return {
      id: user.id,
      display_name: user.display_name,
    };
  }

  @Post()
  async createUser(@Body() body: CreateUserDto) {
    const user = await this.usersService.createUser(body);
    return { id: user.id };
  }
}
