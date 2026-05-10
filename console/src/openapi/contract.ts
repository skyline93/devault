/**
 * Typed surface for control-plane OpenAPI（`npm run codegen` 生成 `api-types.d.ts`）。
 */
import type { components, paths } from './api-types';

/** JSON body for `GET /api/v1/auth/session`. */
export type AuthSessionResponse =
  paths['/api/v1/auth/session']['get']['responses']['200']['content']['application/json'];

export type AuthSessionOutSchema = components['schemas']['AuthSessionOut'];

type _AuthSessionResponseExtendsSchema = AuthSessionResponse extends AuthSessionOutSchema
  ? true
  : never;

export type OpenapiAuthSessionContract = _AuthSessionResponseExtendsSchema;

/** 运行时引用，确保本模块随应用构建参与类型检查。 */
export const openapiAuthSessionContract: OpenapiAuthSessionContract = true;
