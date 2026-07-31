import * as bcrypt from 'bcrypt';

export async function hashPassword(value: string): Promise<string> {
  return bcrypt.hash(value, 10);
}

export async function comparePassword(
  value: string,
  hash: string,
): Promise<boolean> {
  return bcrypt.compare(value, hash);
}
