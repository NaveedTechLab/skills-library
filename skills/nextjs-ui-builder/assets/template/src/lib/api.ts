const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const error = await res.json().catch(() => ({ message: 'Request failed' }));
    throw new ApiError(res.status, error.message || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  get: async <T>(path: string, options?: RequestInit): Promise<T> => {
    const res = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });
    return handleResponse<T>(res);
  },

  post: async <T>(path: string, data: unknown, options?: RequestInit): Promise<T> => {
    const res = await fetch(`${API_URL}${path}`, {
      method: 'POST',
      body: JSON.stringify(data),
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });
    return handleResponse<T>(res);
  },

  put: async <T>(path: string, data: unknown, options?: RequestInit): Promise<T> => {
    const res = await fetch(`${API_URL}${path}`, {
      method: 'PUT',
      body: JSON.stringify(data),
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });
    return handleResponse<T>(res);
  },

  delete: async <T>(path: string, options?: RequestInit): Promise<T> => {
    const res = await fetch(`${API_URL}${path}`, {
      method: 'DELETE',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });
    return handleResponse<T>(res);
  },
};
