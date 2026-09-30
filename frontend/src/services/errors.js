const firstMessage = (value) => {
  if (typeof value === "string" && value.trim()) return value.trim();
  if (Array.isArray(value)) {
    for (const item of value) {
      const message = firstMessage(item);
      if (message) return message;
    }
  }
  if (value && typeof value === "object") {
    for (const [field, messages] of Object.entries(value)) {
      const message = firstMessage(messages);
      if (message) return `${field}: ${message}`;
    }
  }
  return "";
};

export function getFriendlyApiError(error, {
  fallback = "Something went wrong. Please try again.",
  unauthorized = "Your session expired. Please sign in again.",
} = {}) {
  const status = error?.response?.status;
  const data = error?.response?.data;

  if (!error?.response) {
    return "Noya couldn't reach its servers. Check your connection and try again.";
  }
  if (status === 401) return unauthorized;
  if (status === 429) return "Too many requests right now. Please wait a moment and try again.";
  if (status >= 500) return "Noya's server had a problem. Please try again later.";

  return firstMessage(data?.detail || data?.error || data) || fallback;
}
