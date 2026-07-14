import type { ApiErrorBody, ApiErrorResponse, ApiMetaPayload, ApiResponse, HealthPayload } from "./contracts";

export class ApiClientError extends Error {
  constructor(
    readonly status: number,
    readonly error: ApiErrorBody,
  ) {
    super(error.message);
    this.name = "ApiClientError";
  }
}

type FetchLike = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

export class ApiClient {
  constructor(
    private readonly baseUrl = "",
    private readonly fetcher: FetchLike = fetch,
  ) {}

  health(): Promise<ApiResponse<HealthPayload>> {
    return this.get<HealthPayload>("/health");
  }

  meta(): Promise<ApiResponse<ApiMetaPayload>> {
    return this.get<ApiMetaPayload>("/api/v1/meta");
  }

  private async get<TData>(path: string): Promise<ApiResponse<TData>> {
    const response = await this.fetcher(this.url(path), {
      headers: {
        Accept: "application/json",
      },
    });
    const body = (await response.json()) as ApiResponse<TData> | ApiErrorResponse;

    if (!response.ok) {
      const errorBody = body as ApiErrorResponse;
      throw new ApiClientError(response.status, errorBody.error);
    }

    return body as ApiResponse<TData>;
  }

  private url(path: string): string {
    return `${this.baseUrl}${path}`;
  }
}
