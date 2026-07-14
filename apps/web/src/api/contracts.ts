export type ResponseMeta = {
  request_id: string;
};

export type ApiResponse<TData> = {
  data: TData;
  meta: ResponseMeta;
};

export type ApiErrorBody = {
  code: string;
  message: string;
  details: Record<string, unknown> | null;
  request_id: string;
};

export type ApiErrorResponse = {
  error: ApiErrorBody;
};

export type HealthPayload = {
  status: "ok";
  service: "yantu-coach-api";
  environment: "dev" | "test" | "prod";
  data_root: string;
};

export type ApiMetaPayload = {
  service: "yantu-coach-api";
  api_version: "v1";
  contract_version: "contract-v1";
  environment: "dev" | "test" | "prod";
  features: string[];
};
