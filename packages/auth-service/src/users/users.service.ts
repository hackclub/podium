import { Inject, Injectable, HttpException, HttpStatus } from '@nestjs/common';
import { eq } from 'drizzle-orm';
import { DRIZZLE_RW, DRIZZLE_RO, type Database, users, type User } from '@podium/shared';

@Injectable()
export class UsersService {
  constructor(
    @Inject(DRIZZLE_RW) private readonly dbRw: Database,
    @Inject(DRIZZLE_RO) private readonly dbRo: Database,
  ) {}

  async findByEmail(email: string): Promise<User | undefined> {
    return this.dbRo.query.users.findFirst({
      where: eq(users.email, email),
    });
  }

  async findById(id: string): Promise<User | undefined> {
    return this.dbRo.query.users.findFirst({
      where: eq(users.id, id),
    });
  }

  async createUser(data: {
    email: string;
    first_name: string;
    last_name?: string | null;
    display_name?: string | null;
    phone?: string | null;
    street_1?: string | null;
    street_2?: string | null;
    city?: string | null;
    state?: string | null;
    zip_code?: string | null;
    country?: string | null;
    dob?: string | null;
  }): Promise<User> {
    const email = data.email.trim().toLowerCase();
    // Check against primary to avoid a race with a concurrent insert on the same email
    const existing = await this.dbRw.query.users.findFirst({
      where: eq(users.email, email),
    });
    if (existing) {
      throw new HttpException('User already exists', HttpStatus.BAD_REQUEST);
    }

    const [user] = await this.dbRw
      .insert(users)
      .values({
        email,
        first_name: data.first_name,
        last_name: data.last_name ?? '',
        display_name: data.display_name ?? '',
        phone: data.phone ?? '',
        street_1: data.street_1 ?? '',
        street_2: data.street_2 ?? '',
        city: data.city ?? '',
        state: data.state ?? '',
        zip_code: data.zip_code ?? '',
        country: data.country ?? '',
        dob: data.dob ?? null,
      })
      .returning();

    return user;
  }

  async updateUser(
    user: User,
    data: Record<string, any>,
  ): Promise<User> {
    const updateData: Record<string, any> = {};
    for (const [key, value] of Object.entries(data)) {
      if (value !== undefined && value !== null) {
        updateData[key] = value;
      }
    }

    if (Object.keys(updateData).length === 0) {
      throw new HttpException(
        'No fields to update',
        HttpStatus.BAD_REQUEST,
      );
    }

    const [updated] = await this.dbRw
      .update(users)
      .set(updateData)
      .where(eq(users.id, user.id))
      .returning();

    return updated;
  }
}
