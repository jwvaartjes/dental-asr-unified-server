/**
 * TypeScript interfaces for Mondplan Speech User Management API
 * Generated from FastAPI backend schemas
 */

// ============================================================================
// Enums
// ============================================================================

export enum UserRole {
  USER = 'user',
  ADMIN = 'admin',
  SUPER_ADMIN = 'super_admin'
}

export enum UserStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive'
}

export enum BulkOperationAction {
  ACTIVATE = 'activate',
  DEACTIVATE = 'deactivate',
  DELETE = 'delete',
  MAKE_ADMIN = 'make_admin',
  REMOVE_ADMIN = 'remove_admin'
}

// ============================================================================
// User Interfaces
// ============================================================================

export interface UserPermissions {
  canManageUsers: boolean;
  canDeleteUsers: boolean;
  canModifyAdminRoles: boolean;
  isSuperAdmin: boolean;
}

export interface UserBase {
  email: string;
  name?: string | null;
  role: UserRole;
  status: UserStatus;
}

export interface User extends UserBase {
  id: string;
  login_count: number;
  last_login?: string | null;
  last_login_ip?: string | null;
  created_at: string;
  updated_at: string;
  permissions?: UserPermissions | null;
}

export interface UserCreate extends UserBase {
  password?: string | null;
}

export interface UserUpdate {
  name?: string | null;
  role?: UserRole | null;
  status?: UserStatus | null;
}

export interface UserActivity {
  id: string;
  user_id: string;
  admin_id?: string | null;
  action: string;
  details: Record<string, any>;
  ip_address?: string | null;
  user_agent?: string | null;
  created_at: string;
}

// ============================================================================
// Request Interfaces
// ============================================================================

export interface LoginRequest {
  email: string;
  password?: string;
}

export interface MagicLoginRequest {
  email: string;
}

export interface CheckEmailRequest {
  email: string;
}

export interface BulkOperationRequest {
  action: BulkOperationAction;
  user_ids: string[];
}

export interface UserListParams {
  page?: number;
  limit?: number;
  search?: string;
  status?: 'active' | 'inactive' | 'all';
  role?: 'user' | 'admin' | 'all';
  sort_by?: 'email' | 'name' | 'created_at' | 'last_login';
  sort_order?: 'asc' | 'desc';
}

export interface GetUserParams {
  include_activity?: boolean;
}

// ============================================================================
// Response Interfaces
// ============================================================================

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  detail?: string; // For error responses
}

export interface LoginResponse {
  success: true;
  token: string;
  user: {
    id: string;
    email: string;
    name: string;
    role: UserRole;
    permissions: UserPermissions;
  };
}

export interface CheckEmailResponse {
  exists: boolean;
  message: string;
}

export interface VerifyAuthResponse {
  authenticated: boolean;
  user: string;
}

export interface PaginationInfo {
  page: number;
  limit: number;
  total: number;
  total_pages: number;
}

export interface UserListResponse {
  success: true;
  data: {
    users: User[];
    pagination: PaginationInfo;
  };
}

export interface UserResponse {
  success: true;
  data: User & {
    activity_log?: Array<{
      action: string;
      timestamp: string;
      ip_address?: string | null;
      details: Record<string, any>;
    }>;
  };
}

export interface UserStatsResponse {
  success: true;
  data: {
    total_users: number;
    active_users: number;
    inactive_users: number;
    admin_users: number;
    recent_registrations: any[];
    recent_logins: any[];
  };
}

export interface BulkOperationResponse {
  success: true;
  message: string;
  data: {
    processed: number;
    failed: number;
    errors: string[];
  };
}

export interface SimpleActionResponse {
  success: true;
  message: string;
}

// ============================================================================
// Error Interfaces
// ============================================================================

export interface ApiError {
  detail: string;
  status?: number;
}

export interface ValidationError {
  detail: Array<{
    loc: string[];
    msg: string;
    type: string;
  }>;
}

// ============================================================================
// WebSocket Interfaces (for future real-time features)
// ============================================================================

export interface WebSocketMessage {
  type: string;
  payload: any;
  timestamp: string;
}

export interface UserStatusUpdateMessage extends WebSocketMessage {
  type: 'user_status_update';
  payload: {
    user_id: string;
    status: UserStatus;
    updated_by: string;
  };
}

export interface UserRoleUpdateMessage extends WebSocketMessage {
  type: 'user_role_update';
  payload: {
    user_id: string;
    role: UserRole;
    updated_by: string;
  };
}

// ============================================================================
// Utility Types
// ============================================================================

export type SortField = 'email' | 'name' | 'created_at' | 'last_login';
export type SortOrder = 'asc' | 'desc';
export type StatusFilter = 'active' | 'inactive' | 'all';
export type RoleFilter = 'user' | 'admin' | 'all';

// ============================================================================
// Form Types (for React Hook Form or similar)
// ============================================================================

export interface UserFormData {
  name: string;
  email: string;
  role: UserRole;
  status: UserStatus;
}

export interface LoginFormData {
  email: string;
  password?: string;
}

export interface UserSearchFormData {
  search: string;
  status: StatusFilter;
  role: RoleFilter;
  sort_by: SortField;
  sort_order: SortOrder;
}

// ============================================================================
// Table/Grid Types (for data tables)
// ============================================================================

export interface UserTableColumn {
  key: keyof User | 'actions';
  label: string;
  sortable?: boolean;
  width?: string;
  render?: (user: User) => React.ReactNode;
}

export interface UserTableSelection {
  selectedUsers: string[];
  isAllSelected: boolean;
  isPartiallySelected: boolean;
}

// ============================================================================
// Auth Context Types
// ============================================================================

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  permissions: UserPermissions;
}

export interface AuthContextType {
  user: AuthUser | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password?: string) => Promise<void>;
  magicLogin: (email: string) => Promise<void>;
  logout: () => void;
  checkPermission: (permission: keyof UserPermissions) => boolean;
  hasRole: (role: UserRole | UserRole[]) => boolean;
  refreshUser: () => Promise<void>;
}

// ============================================================================
// API Client Types
// ============================================================================

export interface ApiClientOptions {
  baseURL: string;
  timeout?: number;
  retries?: number;
  onTokenExpired?: () => void;
  onError?: (error: ApiError) => void;
}

export interface RequestOptions {
  headers?: Record<string, string>;
  params?: Record<string, any>;
  timeout?: number;
  retries?: number;
}

// ============================================================================
// Component Prop Types
// ============================================================================

export interface UserListComponentProps {
  users: User[];
  loading: boolean;
  pagination: PaginationInfo;
  onPageChange: (page: number) => void;
  onSearch: (query: string) => void;
  onSort: (field: SortField, order: SortOrder) => void;
  onUserSelect: (userIds: string[]) => void;
  onUserAction: (action: BulkOperationAction, userIds: string[]) => void;
}

export interface UserFormComponentProps {
  user?: User;
  onSubmit: (data: UserFormData) => Promise<void>;
  onCancel: () => void;
  loading?: boolean;
  mode: 'create' | 'edit';
}

export interface PermissionGuardProps {
  permission?: keyof UserPermissions;
  role?: UserRole | UserRole[];
  fallback?: React.ReactNode;
  children: React.ReactNode;
}

// ============================================================================
// Hook Types
// ============================================================================

export interface UseUsersOptions {
  page?: number;
  limit?: number;
  search?: string;
  status?: StatusFilter;
  role?: RoleFilter;
  sort_by?: SortField;
  sort_order?: SortOrder;
  enabled?: boolean;
}

export interface UseUsersReturn {
  users: User[];
  pagination: PaginationInfo;
  loading: boolean;
  error: ApiError | null;
  refetch: () => Promise<void>;
  updateUser: (userId: string, data: UserUpdate) => Promise<void>;
  deleteUser: (userId: string) => Promise<void>;
  bulkOperation: (action: BulkOperationAction, userIds: string[]) => Promise<void>;
}

export interface UseUserReturn {
  user: User | null;
  loading: boolean;
  error: ApiError | null;
  refetch: () => Promise<void>;
  update: (data: UserUpdate) => Promise<void>;
  activate: () => Promise<void>;
  deactivate: () => Promise<void>;
  makeAdmin: () => Promise<void>;
  removeAdmin: () => Promise<void>;
  delete: () => Promise<void>;
}

// ============================================================================
// Constants
// ============================================================================

export const USER_ROLE_LABELS: Record<UserRole, string> = {
  [UserRole.USER]: 'User',
  [UserRole.ADMIN]: 'Admin',
  [UserRole.SUPER_ADMIN]: 'Super Admin'
};

export const USER_STATUS_LABELS: Record<UserStatus, string> = {
  [UserStatus.ACTIVE]: 'Active',
  [UserStatus.INACTIVE]: 'Inactive'
};

export const BULK_ACTION_LABELS: Record<BulkOperationAction, string> = {
  [BulkOperationAction.ACTIVATE]: 'Activate Users',
  [BulkOperationAction.DEACTIVATE]: 'Deactivate Users',
  [BulkOperationAction.DELETE]: 'Delete Users',
  [BulkOperationAction.MAKE_ADMIN]: 'Make Admins',
  [BulkOperationAction.REMOVE_ADMIN]: 'Remove Admin Rights'
};

// ============================================================================
// Type Guards
// ============================================================================

export function isApiError(error: any): error is ApiError {
  return error && typeof error.detail === 'string';
}

export function isValidationError(error: any): error is ValidationError {
  return error && Array.isArray(error.detail) && error.detail.length > 0 && error.detail[0].msg;
}

export function isUserRole(role: string): role is UserRole {
  return Object.values(UserRole).includes(role as UserRole);
}

export function isUserStatus(status: string): status is UserStatus {
  return Object.values(UserStatus).includes(status as UserStatus);
}

export function hasPermission(user: AuthUser | null, permission: keyof UserPermissions): boolean {
  return user?.permissions?.[permission] ?? false;
}

export function hasRole(user: AuthUser | null, roles: UserRole | UserRole[]): boolean {
  if (!user) return false;
  const roleArray = Array.isArray(roles) ? roles : [roles];
  return roleArray.includes(user.role);
}

export function canManageUser(currentUser: AuthUser | null, targetUser: User): boolean {
  if (!currentUser || !hasPermission(currentUser, 'canManageUsers')) return false;

  // Can't manage yourself
  if (currentUser.id === targetUser.id) return false;

  // Super admin can manage anyone except other super admins
  if (currentUser.role === UserRole.SUPER_ADMIN) {
    return targetUser.role !== UserRole.SUPER_ADMIN || currentUser.id === targetUser.id;
  }

  // Admin can only manage regular users
  if (currentUser.role === UserRole.ADMIN) {
    return targetUser.role === UserRole.USER;
  }

  return false;
}