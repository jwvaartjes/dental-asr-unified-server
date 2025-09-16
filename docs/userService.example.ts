/**
 * Example User Management Service for React/TypeScript
 * Ready-to-use service class for Mondplan Speech User Management API
 */

import {
  User,
  UserUpdate,
  UserListParams,
  GetUserParams,
  LoginRequest,
  MagicLoginRequest,
  BulkOperationRequest,
  BulkOperationAction,
  LoginResponse,
  UserListResponse,
  UserResponse,
  UserStatsResponse,
  BulkOperationResponse,
  CheckEmailResponse,
  VerifyAuthResponse,
  SimpleActionResponse,
  ApiError,
  ApiClientOptions,
  RequestOptions,
  AuthUser
} from './frontend-types';

export class UserManagementService {
  private baseURL: string;
  private token: string | null = null;
  private timeout: number;
  private onTokenExpired?: () => void;
  private onError?: (error: ApiError) => void;

  constructor(options: ApiClientOptions) {
    this.baseURL = options.baseURL.replace(/\/$/, ''); // Remove trailing slash
    this.timeout = options.timeout || 10000;
    this.onTokenExpired = options.onTokenExpired;
    this.onError = options.onError;

    // Load token from localStorage on initialization
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('jwt_token');
    }
  }

  // ============================================================================
  // Private Helper Methods
  // ============================================================================

  private async request<T>(
    endpoint: string,
    options: RequestInit & { timeout?: number } = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    const timeout = options.timeout || this.timeout;

    const config: RequestInit = {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    // Add Authorization header if token exists
    if (this.token && config.headers) {
      (config.headers as Record<string, string>)['Authorization'] = `Bearer ${this.token}`;
    }

    try {
      // Create timeout promise
      const timeoutPromise = new Promise<never>((_, reject) => {
        setTimeout(() => reject(new Error('Request timeout')), timeout);
      });

      // Make the request with timeout
      const response = await Promise.race([
        fetch(url, config),
        timeoutPromise
      ]);

      // Handle HTTP errors
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));

        // Handle specific error cases
        if (response.status === 401) {
          this.handleTokenExpired();
          throw new ApiError('Authentication required', 401);
        }

        const error = new ApiError(errorData.detail || `HTTP ${response.status}`, response.status);
        this.onError?.(error);
        throw error;
      }

      return await response.json();
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }

      const apiError = new ApiError(
        error instanceof Error ? error.message : 'Network error',
        0
      );
      this.onError?.(apiError);
      throw apiError;
    }
  }

  private handleTokenExpired(): void {
    this.token = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('jwt_token');
    }
    this.onTokenExpired?.();
  }

  private setToken(token: string): void {
    this.token = token;
    if (typeof window !== 'undefined') {
      localStorage.setItem('jwt_token', token);
    }
  }

  private buildQueryString(params: Record<string, any>): string {
    const searchParams = new URLSearchParams();

    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        searchParams.append(key, String(value));
      }
    });

    const queryString = searchParams.toString();
    return queryString ? `?${queryString}` : '';
  }

  // ============================================================================
  // Authentication Methods
  // ============================================================================

  async magicLogin(data: MagicLoginRequest): Promise<AuthUser> {
    const response = await this.request<LoginResponse>('/api/auth/login-magic', {
      method: 'POST',
      body: JSON.stringify(data),
    });

    this.setToken(response.token);
    return {
      id: response.user.id,
      email: response.user.email,
      name: response.user.name,
      role: response.user.role,
      permissions: response.user.permissions,
    };
  }

  async login(data: LoginRequest): Promise<AuthUser> {
    const response = await this.request<LoginResponse>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    });

    this.setToken(response.token);
    return {
      id: response.user.id,
      email: response.user.email,
      name: response.user.name,
      role: response.user.role,
      permissions: response.user.permissions,
    };
  }

  async checkEmail(email: string): Promise<CheckEmailResponse> {
    return this.request<CheckEmailResponse>(`/api/auth/check-email?email=${encodeURIComponent(email)}`);
  }

  async verifyAuth(): Promise<VerifyAuthResponse> {
    return this.request<VerifyAuthResponse>('/api/auth/verify');
  }

  logout(): void {
    this.token = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('jwt_token');
    }
  }

  isAuthenticated(): boolean {
    return !!this.token;
  }

  getToken(): string | null {
    return this.token;
  }

  // ============================================================================
  // User Management Methods
  // ============================================================================

  async getUsers(params: UserListParams = {}): Promise<UserListResponse> {
    const queryString = this.buildQueryString(params);
    return this.request<UserListResponse>(`/api/users/${queryString}`);
  }

  async getUserStats(): Promise<UserStatsResponse> {
    return this.request<UserStatsResponse>('/api/users/stats');
  }

  async getUser(userId: string, params: GetUserParams = {}): Promise<UserResponse> {
    const queryString = this.buildQueryString(params);
    return this.request<UserResponse>(`/api/users/${userId}${queryString}`);
  }

  async updateUser(userId: string, data: UserUpdate): Promise<UserResponse> {
    return this.request<UserResponse>(`/api/users/${userId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async activateUser(userId: string): Promise<SimpleActionResponse> {
    return this.request<SimpleActionResponse>(`/api/users/${userId}/activate`, {
      method: 'POST',
    });
  }

  async deactivateUser(userId: string): Promise<SimpleActionResponse> {
    return this.request<SimpleActionResponse>(`/api/users/${userId}/deactivate`, {
      method: 'POST',
    });
  }

  async makeAdmin(userId: string): Promise<SimpleActionResponse> {
    return this.request<SimpleActionResponse>(`/api/users/${userId}/make-admin`, {
      method: 'POST',
    });
  }

  async removeAdmin(userId: string): Promise<SimpleActionResponse> {
    return this.request<SimpleActionResponse>(`/api/users/${userId}/remove-admin`, {
      method: 'POST',
    });
  }

  async deleteUser(userId: string): Promise<SimpleActionResponse> {
    return this.request<SimpleActionResponse>(`/api/users/${userId}`, {
      method: 'DELETE',
    });
  }

  async bulkOperation(data: BulkOperationRequest): Promise<BulkOperationResponse> {
    return this.request<BulkOperationResponse>('/api/users/bulk', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getMyProfile(): Promise<UserResponse> {
    return this.request<UserResponse>('/api/users/me/profile');
  }

  // ============================================================================
  // Convenience Methods
  // ============================================================================

  async searchUsers(query: string, options: Omit<UserListParams, 'search'> = {}): Promise<UserListResponse> {
    return this.getUsers({ ...options, search: query });
  }

  async getUsersByStatus(status: 'active' | 'inactive', options: Omit<UserListParams, 'status'> = {}): Promise<UserListResponse> {
    return this.getUsers({ ...options, status });
  }

  async getUsersByRole(role: 'user' | 'admin', options: Omit<UserListParams, 'role'> = {}): Promise<UserListResponse> {
    return this.getUsers({ ...options, role });
  }

  async activateMultipleUsers(userIds: string[]): Promise<BulkOperationResponse> {
    return this.bulkOperation({
      action: BulkOperationAction.ACTIVATE,
      user_ids: userIds,
    });
  }

  async deactivateMultipleUsers(userIds: string[]): Promise<BulkOperationResponse> {
    return this.bulkOperation({
      action: BulkOperationAction.DEACTIVATE,
      user_ids: userIds,
    });
  }

  async deleteMultipleUsers(userIds: string[]): Promise<BulkOperationResponse> {
    return this.bulkOperation({
      action: BulkOperationAction.DELETE,
      user_ids: userIds,
    });
  }
}

// ============================================================================
// Custom API Error Class
// ============================================================================

export class ApiError extends Error {
  public status: number;
  public detail: string;

  constructor(detail: string, status: number = 0) {
    super(detail);
    this.name = 'ApiError';
    this.detail = detail;
    this.status = status;
  }

  isUnauthorized(): boolean {
    return this.status === 401;
  }

  isForbidden(): boolean {
    return this.status === 403;
  }

  isNotFound(): boolean {
    return this.status === 404;
  }

  isValidationError(): boolean {
    return this.status === 400;
  }

  isTooManyRequests(): boolean {
    return this.status === 429;
  }

  isServerError(): boolean {
    return this.status >= 500;
  }
}

// ============================================================================
// React Hook Examples
// ============================================================================

import { useState, useEffect, useCallback } from 'react';
import { UserRole, UserPermissions } from './frontend-types';

// Example: useAuth hook
export function useAuth(userService: UserManagementService) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);

  const checkAuth = useCallback(async () => {
    if (!userService.isAuthenticated()) {
      setLoading(false);
      return;
    }

    try {
      await userService.verifyAuth();
      const profileResponse = await userService.getMyProfile();
      setUser({
        id: profileResponse.data.id,
        email: profileResponse.data.email,
        name: profileResponse.data.name || '',
        role: profileResponse.data.role,
        permissions: profileResponse.data.permissions || {
          canManageUsers: false,
          canDeleteUsers: false,
          canModifyAdminRoles: false,
          isSuperAdmin: false,
        },
      });
      setError(null);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err);
        if (err.isUnauthorized()) {
          setUser(null);
        }
      }
    } finally {
      setLoading(false);
    }
  }, [userService]);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const login = useCallback(async (email: string, password?: string) => {
    setLoading(true);
    setError(null);
    try {
      const authUser = password
        ? await userService.login({ email, password })
        : await userService.magicLogin({ email });
      setUser(authUser);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err);
      }
    } finally {
      setLoading(false);
    }
  }, [userService]);

  const logout = useCallback(() => {
    userService.logout();
    setUser(null);
    setError(null);
  }, [userService]);

  const hasPermission = useCallback((permission: keyof UserPermissions): boolean => {
    return user?.permissions?.[permission] ?? false;
  }, [user]);

  const hasRole = useCallback((roles: UserRole | UserRole[]): boolean => {
    if (!user) return false;
    const roleArray = Array.isArray(roles) ? roles : [roles];
    return roleArray.includes(user.role);
  }, [user]);

  return {
    user,
    loading,
    error,
    isAuthenticated: !!user,
    login,
    logout,
    hasPermission,
    hasRole,
    refreshUser: checkAuth,
  };
}

// Example: useUsers hook
export function useUsers(
  userService: UserManagementService,
  options: UserListParams = {}
) {
  const [users, setUsers] = useState<User[]>([]);
  const [pagination, setPagination] = useState({
    page: 1,
    limit: 20,
    total: 0,
    total_pages: 0,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const fetchUsers = useCallback(async (params: UserListParams = {}) => {
    setLoading(true);
    setError(null);

    try {
      const response = await userService.getUsers({ ...options, ...params });
      setUsers(response.data.users);
      setPagination(response.data.pagination);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err);
      }
    } finally {
      setLoading(false);
    }
  }, [userService, options]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const updateUser = useCallback(async (userId: string, data: UserUpdate) => {
    try {
      await userService.updateUser(userId, data);
      await fetchUsers(); // Refresh list
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err);
      }
      throw err;
    }
  }, [userService, fetchUsers]);

  const deleteUser = useCallback(async (userId: string) => {
    try {
      await userService.deleteUser(userId);
      await fetchUsers(); // Refresh list
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err);
      }
      throw err;
    }
  }, [userService, fetchUsers]);

  const bulkOperation = useCallback(async (action: BulkOperationAction, userIds: string[]) => {
    try {
      await userService.bulkOperation({ action, user_ids: userIds });
      await fetchUsers(); // Refresh list
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err);
      }
      throw err;
    }
  }, [userService, fetchUsers]);

  return {
    users,
    pagination,
    loading,
    error,
    refetch: fetchUsers,
    updateUser,
    deleteUser,
    bulkOperation,
  };
}

// ============================================================================
// Usage Examples
// ============================================================================

/*
// 1. Initialize the service
const userService = new UserManagementService({
  baseURL: 'http://localhost:8089',
  timeout: 10000,
  onTokenExpired: () => {
    // Redirect to login page
    window.location.href = '/login';
  },
  onError: (error) => {
    // Show toast notification
    console.error('API Error:', error.detail);
  },
});

// 2. Use in a React component
function UserManagement() {
  const auth = useAuth(userService);
  const users = useUsers(userService, {
    page: 1,
    limit: 20,
    status: 'all',
    sort_by: 'created_at',
    sort_order: 'desc'
  });

  if (!auth.isAuthenticated) {
    return <LoginForm onLogin={auth.login} />;
  }

  if (!auth.hasPermission('canManageUsers')) {
    return <div>Access denied</div>;
  }

  return (
    <div>
      <h1>User Management</h1>
      <UserTable
        users={users.users}
        loading={users.loading}
        pagination={users.pagination}
        onUserUpdate={users.updateUser}
        onUserDelete={users.deleteUser}
        onBulkOperation={users.bulkOperation}
      />
    </div>
  );
}

// 3. Direct service usage
async function example() {
  try {
    // Login
    const user = await userService.magicLogin({ email: 'admin@example.com' });
    console.log('Logged in as:', user.name);

    // Get users
    const usersResponse = await userService.getUsers({
      page: 1,
      limit: 10,
      search: 'admin'
    });
    console.log('Found users:', usersResponse.data.users.length);

    // Update user
    await userService.updateUser('user-id', {
      name: 'Updated Name',
      status: 'active'
    });

    // Bulk activate users
    await userService.activateMultipleUsers(['id1', 'id2', 'id3']);

  } catch (error) {
    if (error instanceof ApiError) {
      console.error('API Error:', error.detail);

      if (error.isUnauthorized()) {
        // Handle authentication required
      } else if (error.isForbidden()) {
        // Handle insufficient permissions
      } else if (error.isValidationError()) {
        // Handle validation errors
      }
    }
  }
}
*/