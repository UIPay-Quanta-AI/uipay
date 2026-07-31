import { createHash, timingSafeEqual } from 'crypto';

export function cryptoHash(value: string) {
  return createHash('sha256').update(value).digest('hex');
}

export function verifyHash(inputValue: string, storedHash: string) {
  const inputHash = cryptoHash(inputValue);

  const computed = Buffer.from(inputHash, 'hex');
  const expected = Buffer.from(storedHash, 'hex');

  if (computed.length !== expected.length) {
    return false;
  }

  return timingSafeEqual(computed, expected);
}
