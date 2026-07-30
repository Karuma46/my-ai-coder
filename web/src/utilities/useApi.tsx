import axios from "axios";
import type { AxiosRequestConfig, AxiosResponse } from "axios";
import { useCallback, useState } from "react";
import { getAccessToken } from "./authToken";

const DEFAULT_TIMEOUT = 10_000;
const DEFAULT_RETRIES = 0;
const DEFAULT_RETRY_DELAY = 300;

export type ApiParameters = Record<string, unknown>;

export type ApiResult<TData> = {
  data: TData;
};

export type UseApiOptions = {
  timeout?: number;
  retries?: number;
  retryDelay?: number;
};

export type ApiRequestConfig<TParameters = unknown> =
  AxiosRequestConfig<TParameters> & {
    retries?: number;
    retryDelay?: number;
  };

type RetryOptions = {
  retries: number;
  retryDelay: number;
};

type PreparedRequestConfig<TParameters> = {
  axiosConfig: AxiosRequestConfig<TParameters>;
  retryOptions: RetryOptions;
};

export type UseApiResult<TData> = {
  data: TData | null;
  get: (
    endpoint: string,
    parameters?: ApiParameters,
    config?: ApiRequestConfig,
  ) => Promise<ApiResult<TData>>;
  post: <TParameters = undefined>(
    endpoint: string,
    parameters?: TParameters,
    config?: ApiRequestConfig<TParameters | undefined>,
  ) => Promise<ApiResult<TData>>;
  postUpload: (
    endpoint: string,
    formData: FormData,
    config?: ApiRequestConfig<FormData>,
  ) => Promise<ApiResult<TData>>;
  put: <TParameters = undefined>(
    endpoint: string,
    parameters?: TParameters,
    config?: ApiRequestConfig<TParameters | undefined>,
  ) => Promise<ApiResult<TData>>;
  patch: <TParameters = undefined>(
    endpoint: string,
    parameters?: TParameters,
    config?: ApiRequestConfig<TParameters | undefined>,
  ) => Promise<ApiResult<TData>>;
  patchUpload: (
    endpoint: string,
    formData: FormData,
    config?: ApiRequestConfig<FormData>,
  ) => Promise<ApiResult<TData>>;
  delete: (
    endpoint: string,
    parameters?: ApiParameters,
    config?: ApiRequestConfig,
  ) => Promise<ApiResult<TData>>;
};

function normalizeDuration(value: number | undefined, fallback: number) {
  return value !== undefined && Number.isFinite(value) && value >= 0
    ? value
    : fallback;
}

function normalizeRetries(value: number | undefined, fallback: number) {
  return value !== undefined && Number.isFinite(value) && value >= 0
    ? Math.floor(value)
    : fallback;
}

function prepareRequestConfig<TParameters>(
  config: ApiRequestConfig<TParameters> | undefined,
  defaults: Required<UseApiOptions>,
): PreparedRequestConfig<TParameters> {
  const { retries, retryDelay, ...axiosConfig } = config ?? {};
  const accessToken = getAccessToken();

  return {
    axiosConfig: {
      ...axiosConfig,
      headers: accessToken
        ? {
            Authorization: `Bearer ${accessToken}`,
            ...axiosConfig.headers,
          }
        : axiosConfig.headers,
      timeout: normalizeDuration(axiosConfig.timeout, defaults.timeout),
    },
    retryOptions: {
      retries: normalizeRetries(retries, defaults.retries),
      retryDelay: normalizeDuration(retryDelay, defaults.retryDelay),
    },
  };
}

function isRetryableError(error: unknown) {
  if (!axios.isAxiosError(error) || error.code === "ERR_CANCELED") {
    return false;
  }

  const status = error.response?.status;

  return (
    status === undefined || status === 408 || status === 429 || status >= 500
  );
}

function wait(delay: number) {
  return new Promise<void>((resolve) => {
    setTimeout(resolve, delay);
  });
}

async function executeWithRetry<TData>(
  request: () => Promise<AxiosResponse<TData>>,
  options: RetryOptions,
) {
  let attempt = 0;

  while (true) {
    try {
      return await request();
    } catch (error) {
      if (attempt >= options.retries || !isRetryableError(error)) {
        throw error;
      }

      const delay = options.retryDelay * 2 ** attempt;
      attempt += 1;

      if (delay > 0) {
        await wait(delay);
      }
    }
  }
}

export function useApi<TData = unknown>(
  options: UseApiOptions = {},
): UseApiResult<TData> {
  const [data, setData] = useState<TData | null>(null);
  const timeout = normalizeDuration(options.timeout, DEFAULT_TIMEOUT);
  const retries = normalizeRetries(options.retries, DEFAULT_RETRIES);
  const retryDelay = normalizeDuration(
    options.retryDelay,
    DEFAULT_RETRY_DELAY,
  );

  const resolveRequest = useCallback(
    async (
      request: () => Promise<AxiosResponse<TData>>,
      retryOptions: RetryOptions,
    ): Promise<ApiResult<TData>> => {
      const response = await executeWithRetry(request, retryOptions);
      setData(response.data);

      return { data: response.data };
    },
    [],
  );

  const get = useCallback(
    (
      endpoint: string,
      parameters?: ApiParameters,
      config?: ApiRequestConfig,
    ) => {
      const prepared = prepareRequestConfig(config, {
        timeout,
        retries,
        retryDelay,
      });

      return resolveRequest(
        () =>
          axios.get<TData>(endpoint, {
            ...prepared.axiosConfig,
            params: parameters ?? prepared.axiosConfig.params,
          }),
        prepared.retryOptions,
      );
    },
    [resolveRequest, retries, retryDelay, timeout],
  );

  const post = useCallback(
    <TParameters = undefined,>(
      endpoint: string,
      parameters?: TParameters,
      config?: ApiRequestConfig<TParameters | undefined>,
    ) => {
      const prepared = prepareRequestConfig(config, {
        timeout,
        retries,
        retryDelay,
      });

      return resolveRequest(
        () =>
          axios.post<TData, AxiosResponse<TData>, TParameters | undefined>(
            endpoint,
            parameters,
            prepared.axiosConfig,
          ),
        prepared.retryOptions,
      );
    },
    [resolveRequest, retries, retryDelay, timeout],
  );

  const postUpload = useCallback(
    (
      endpoint: string,
      formData: FormData,
      config?: ApiRequestConfig<FormData>,
    ) => {
      const prepared = prepareRequestConfig(config, {
        timeout,
        retries,
        retryDelay,
      });

      return resolveRequest(
        () =>
          axios.post<TData, AxiosResponse<TData>, FormData>(
            endpoint,
            formData,
            prepared.axiosConfig,
          ),
        prepared.retryOptions,
      );
    },
    [resolveRequest, retries, retryDelay, timeout],
  );

  const put = useCallback(
    <TParameters = undefined,>(
      endpoint: string,
      parameters?: TParameters,
      config?: ApiRequestConfig<TParameters | undefined>,
    ) => {
      const prepared = prepareRequestConfig(config, {
        timeout,
        retries,
        retryDelay,
      });

      return resolveRequest(
        () =>
          axios.put<TData, AxiosResponse<TData>, TParameters | undefined>(
            endpoint,
            parameters,
            prepared.axiosConfig,
          ),
        prepared.retryOptions,
      );
    },
    [resolveRequest, retries, retryDelay, timeout],
  );

  const patch = useCallback(
    <TParameters = undefined,>(
      endpoint: string,
      parameters?: TParameters,
      config?: ApiRequestConfig<TParameters | undefined>,
    ) => {
      const prepared = prepareRequestConfig(config, {
        timeout,
        retries,
        retryDelay,
      });

      return resolveRequest(
        () =>
          axios.patch<TData, AxiosResponse<TData>, TParameters | undefined>(
            endpoint,
            parameters,
            prepared.axiosConfig,
          ),
        prepared.retryOptions,
      );
    },
    [resolveRequest, retries, retryDelay, timeout],
  );

  const patchUpload = useCallback(
    (
      endpoint: string,
      formData: FormData,
      config?: ApiRequestConfig<FormData>,
    ) => {
      const prepared = prepareRequestConfig(config, {
        timeout,
        retries,
        retryDelay,
      });

      return resolveRequest(
        () =>
          axios.patch<TData, AxiosResponse<TData>, FormData>(
            endpoint,
            formData,
            prepared.axiosConfig,
          ),
        prepared.retryOptions,
      );
    },
    [resolveRequest, retries, retryDelay, timeout],
  );

  const deleteRequest = useCallback(
    (
      endpoint: string,
      parameters?: ApiParameters,
      config?: ApiRequestConfig,
    ) => {
      const prepared = prepareRequestConfig(config, {
        timeout,
        retries,
        retryDelay,
      });

      return resolveRequest(
        () =>
          axios.delete<TData>(endpoint, {
            ...prepared.axiosConfig,
            params: parameters ?? prepared.axiosConfig.params,
          }),
        prepared.retryOptions,
      );
    },
    [resolveRequest, retries, retryDelay, timeout],
  );

  return {
    data,
    get,
    post,
    postUpload,
    put,
    patch,
    patchUpload,
    delete: deleteRequest,
  };
}
