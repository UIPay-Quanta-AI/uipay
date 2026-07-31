export function successResponse<T>(message: string, data: T) {
  return {
    status: 'success' as const,
    message,
    data,
  };
}
