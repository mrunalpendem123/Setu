use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::{get, post},
    Json, Router,
};
use reqwest::Method;
use serde_json::{json, Value};
use std::{collections::HashMap, net::SocketAddr, sync::Arc, time::Duration};
use thiserror::Error;
use tracing::info;

#[derive(Clone)]
struct AppState {
    base_url: String,
    api_key: String,
    publishable_key: Option<String>,
    admin_key: Option<String>,
    vault_key: Option<String>,
    api_key_header: String,
    merchant_id: Option<String>,
    timeout_seconds: u64,
    max_retries: usize,
    retry_backoff_ms: u64,
}

#[derive(Error, Debug)]
enum ApiError {
    #[error("missing_env:{0}")]
    MissingEnv(String),
    #[error("http_error:{0}")]
    HttpError(String),
    #[error("upstream_error")]
    Upstream(StatusCode, Value),
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        match self {
            ApiError::MissingEnv(name) => {
                (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": name}))).into_response()
            }
            ApiError::HttpError(message) => {
                (StatusCode::BAD_GATEWAY, Json(json!({"error": message}))).into_response()
            }
            ApiError::Upstream(code, payload) => (code, Json(payload)).into_response(),
        }
    }
}

#[derive(Clone, Copy)]
enum KeyType {
    Secret,
    Publishable,
    Admin,
    Vault,
}


fn env_string(key: &str) -> Result<String, ApiError> {
    std::env::var(key).map_err(|_| ApiError::MissingEnv(key.to_string()))
}

fn env_optional(key: &str) -> Option<String> {
    std::env::var(key).ok()
}

fn env_u64(key: &str, default: u64) -> u64 {
    std::env::var(key).ok().and_then(|v| v.parse().ok()).unwrap_or(default)
}

fn env_usize(key: &str, default: usize) -> usize {
    std::env::var(key).ok().and_then(|v| v.parse().ok()).unwrap_or(default)
}

async fn hyperswitch_request(
    state: &AppState,
    method: Method,
    path: &str,
    key_type: KeyType,
    body: Option<Value>,
    query: Option<HashMap<String, String>>,
) -> Result<Value, ApiError> {
    let key = match key_type {
        KeyType::Secret => state.api_key.clone(),
        KeyType::Publishable => state
            .publishable_key
            .clone()
            .ok_or_else(|| ApiError::MissingEnv("HYPERSWITCH_PUBLISHABLE_KEY".to_string()))?,
        KeyType::Admin => state
            .admin_key
            .clone()
            .ok_or_else(|| ApiError::MissingEnv("HYPERSWITCH_ADMIN_API_KEY".to_string()))?,
        KeyType::Vault => state
            .vault_key
            .clone()
            .ok_or_else(|| ApiError::MissingEnv("HYPERSWITCH_VAULT_API_KEY".to_string()))?,
    };

    let url = format!("{}{}", state.base_url, path);
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(state.timeout_seconds))
        .build()
        .map_err(|err| ApiError::HttpError(err.to_string()))?;

    for attempt in 0..=state.max_retries {
        let mut request = client.request(method.clone(), &url);
        request = request.header(&state.api_key_header, &key);
        request = request.header("Content-Type", "application/json");
        if let Some(ref merchant_id) = state.merchant_id {
            request = request.header("x-merchant-id", merchant_id);
        }
        if let Some(ref body_value) = body {
            request = request.json(body_value);
        }
        if let Some(ref params) = query {
            request = request.query(params);
        }

        let response = request.send().await.map_err(|err| ApiError::HttpError(err.to_string()))?;
        let status = response.status();
        let payload: Value = response.json().await.unwrap_or_else(|_| json!({"message": "invalid_json"}));

        if status.is_success() {
            return Ok(payload);
        }

        let should_retry = status == StatusCode::TOO_MANY_REQUESTS
            || payload
                .get("message")
                .and_then(|v| v.as_str())
                .map(|v| v.to_lowercase().contains("access to this object is restricted"))
                .unwrap_or(false);

        if should_retry && attempt < state.max_retries {
            let backoff = state.retry_backoff_ms * 2u64.pow(attempt as u32);
            tokio::time::sleep(Duration::from_millis(backoff)).await;
            continue;
        }

        return Err(ApiError::Upstream(status, payload));
    }

    Err(ApiError::HttpError("max_retries_exceeded".to_string()))
}

async fn proxy_post(
    State(state): State<Arc<AppState>>,
    path: String,
    key_type: KeyType,
    Json(body): Json<Value>,
) -> Result<Json<Value>, ApiError> {
    let payload = hyperswitch_request(&state, Method::POST, &path, key_type, Some(body), None).await?;
    Ok(Json(payload))
}

async fn proxy_post_optional(
    State(state): State<Arc<AppState>>,
    path: String,
    key_type: KeyType,
    body: Option<Json<Value>>,
) -> Result<Json<Value>, ApiError> {
    let payload = hyperswitch_request(
        &state,
        Method::POST,
        &path,
        key_type,
        Some(body.map(|b| b.0).unwrap_or_else(|| json!({}))),
        None,
    )
    .await?;
    Ok(Json(payload))
}

async fn proxy_get(
    State(state): State<Arc<AppState>>,
    path: String,
    key_type: KeyType,
    Query(params): Query<HashMap<String, String>>,
) -> Result<Json<Value>, ApiError> {
    let payload = hyperswitch_request(&state, Method::GET, &path, key_type, None, Some(params)).await?;
    Ok(Json(payload))
}

async fn create_payment(State(state): State<Arc<AppState>>, Json(body): Json<Value>) -> Result<Json<Value>, ApiError> {
    proxy_post(State(state), "/payments".to_string(), KeyType::Secret, Json(body)).await
}

async fn update_payment(
    State(state): State<Arc<AppState>>,
    Path(payment_id): Path<String>,
    body: Option<Json<Value>>,
) -> Result<Json<Value>, ApiError> {
    proxy_post_optional(
        State(state),
        format!("/payments/{payment_id}"),
        KeyType::Secret,
        body,
    )
    .await
}

async fn confirm_payment(
    State(state): State<Arc<AppState>>,
    Path(payment_id): Path<String>,
    body: Option<Json<Value>>,
) -> Result<Json<Value>, ApiError> {
    proxy_post_optional(
        State(state),
        format!("/payments/{payment_id}/confirm"),
        KeyType::Secret,
        body,
    )
    .await
}

async fn retrieve_payment(
    State(state): State<Arc<AppState>>,
    Path(payment_id): Path<String>,
    Query(params): Query<HashMap<String, String>>,
) -> Result<Json<Value>, ApiError> {
    let payload = hyperswitch_request(
        &state,
        Method::GET,
        &format!("/payments/{payment_id}"),
        KeyType::Secret,
        None,
        Some(params),
    )
    .await?;
    Ok(Json(payload))
}

async fn cancel_payment(
    State(state): State<Arc<AppState>>,
    Path(payment_id): Path<String>,
    body: Option<Json<Value>>,
) -> Result<Json<Value>, ApiError> {
    proxy_post_optional(
        State(state),
        format!("/payments/{payment_id}/cancel"),
        KeyType::Secret,
        body,
    )
    .await
}

async fn cancel_post_capture(
    State(state): State<Arc<AppState>>,
    Path(payment_id): Path<String>,
    body: Option<Json<Value>>,
) -> Result<Json<Value>, ApiError> {
    proxy_post_optional(
        State(state),
        format!("/payments/{payment_id}/cancel_post_capture"),
        KeyType::Secret,
        body,
    )
    .await
}

async fn capture_payment(
    State(state): State<Arc<AppState>>,
    Path(payment_id): Path<String>,
    body: Option<Json<Value>>,
) -> Result<Json<Value>, ApiError> {
    proxy_post_optional(
        State(state),
        format!("/payments/{payment_id}/capture"),
        KeyType::Secret,
        body,
    )
    .await
}

async fn incremental_authorization(
    State(state): State<Arc<AppState>>,
    Path(payment_id): Path<String>,
    body: Option<Json<Value>>,
) -> Result<Json<Value>, ApiError> {
    proxy_post_optional(
        State(state),
        format!("/payments/{payment_id}/incremental_authorization"),
        KeyType::Secret,
        body,
    )
    .await
}

async fn extend_authorization(
    State(state): State<Arc<AppState>>,
    Path(payment_id): Path<String>,
) -> Result<Json<Value>, ApiError> {
    proxy_post_optional(
        State(state),
        format!("/payments/{payment_id}/extend_authorization"),
        KeyType::Secret,
        None,
    )
    .await
}

async fn session_tokens(State(state): State<Arc<AppState>>, Json(body): Json<Value>) -> Result<Json<Value>, ApiError> {
    proxy_post(State(state), "/payments/session_tokens".to_string(), KeyType::Publishable, Json(body)).await
}

async fn payment_link_retrieve(
    State(state): State<Arc<AppState>>,
    Path(link_id): Path<String>,
    Query(params): Query<HashMap<String, String>>,
) -> Result<Json<Value>, ApiError> {
    let payload = hyperswitch_request(
        &state,
        Method::GET,
        &format!("/payment_link/{link_id}"),
        KeyType::Publishable,
        None,
        Some(params),
    )
    .await?;
    Ok(Json(payload))
}

async fn list_payments(
    State(state): State<Arc<AppState>>,
    Query(params): Query<HashMap<String, String>>,
) -> Result<Json<Value>, ApiError> {
    let payload = hyperswitch_request(&state, Method::GET, "/payments/list", KeyType::Secret, None, Some(params)).await?;
    Ok(Json(payload))
}

async fn external_3ds(
    State(state): State<Arc<AppState>>,
    Path(payment_id): Path<String>,
    body: Option<Json<Value>>,
) -> Result<Json<Value>, ApiError> {
    proxy_post_optional(
        State(state),
        format!("/payments/{payment_id}/3ds/authentication"),
        KeyType::Secret,
        body,
    )
    .await
}

async fn complete_authorize(
    State(state): State<Arc<AppState>>,
    Path(payment_id): Path<String>,
    body: Option<Json<Value>>,
) -> Result<Json<Value>, ApiError> {
    proxy_post_optional(
        State(state),
        format!("/{payment_id}/complete_authorize"),
        KeyType::Secret,
        body,
    )
    .await
}

async fn update_metadata(
    State(state): State<Arc<AppState>>,
    Path(payment_id): Path<String>,
    body: Option<Json<Value>>,
) -> Result<Json<Value>, ApiError> {
    proxy_post_optional(
        State(state),
        format!("/payments/{payment_id}/update_metadata"),
        KeyType::Secret,
        body,
    )
    .await
}

async fn submit_eligibility(
    State(state): State<Arc<AppState>>,
    Path(payment_id): Path<String>,
    body: Option<Json<Value>>,
) -> Result<Json<Value>, ApiError> {
    proxy_post_optional(
        State(state),
        format!("/payments/{payment_id}/eligibility"),
        KeyType::Secret,
        body,
    )
    .await
}

async fn payment_method_sessions(
    State(state): State<Arc<AppState>>,
    Json(body): Json<Value>,
) -> Result<Json<Value>, ApiError> {
    let path = std::env::var("HYPERSWITCH_PAYMENT_METHOD_SESSION_PATH")
        .unwrap_or_else(|_| "/v2/payment-method-session".to_string());
    let payload = hyperswitch_request(&state, Method::POST, &path, KeyType::Vault, Some(body), None).await?;
    Ok(Json(payload))
}

async fn create_api_key(
    State(state): State<Arc<AppState>>,
    Path(merchant_id): Path<String>,
    body: Option<Json<Value>>,
) -> Result<Json<Value>, ApiError> {
    proxy_post_optional(
        State(state),
        format!("/api_keys/{merchant_id}"),
        KeyType::Admin,
        body,
    )
    .await
}

#[tokio::main]
async fn main() -> Result<(), ApiError> {
    tracing_subscriber::fmt()
        .with_env_filter("info")
        .init();

    let state = AppState {
        base_url: std::env::var("HYPERSWITCH_BASE_URL").unwrap_or_else(|_| "https://sandbox.hyperswitch.io".to_string()),
        api_key: env_string("HYPERSWITCH_API_KEY")?,
        publishable_key: env_optional("HYPERSWITCH_PUBLISHABLE_KEY"),
        admin_key: env_optional("HYPERSWITCH_ADMIN_API_KEY"),
        vault_key: env_optional("HYPERSWITCH_VAULT_API_KEY"),
        api_key_header: std::env::var("HYPERSWITCH_API_KEY_HEADER").unwrap_or_else(|_| "api-key".to_string()),
        merchant_id: env_optional("HYPERSWITCH_MERCHANT_ID"),
        timeout_seconds: env_u64("HYPERSWITCH_TIMEOUT_SECONDS", 20),
        max_retries: env_usize("HYPERSWITCH_MAX_RETRIES", 3),
        retry_backoff_ms: env_u64("HYPERSWITCH_RETRY_BACKOFF_MS", 200),
    };

    let app = Router::new()
        .route("/health", get(|| async { "ok" }))
        .route("/payments", post(create_payment).get(list_payments))
        .route("/payments/session_tokens", post(session_tokens))
        .route("/payments/:payment_id", post(update_payment).get(retrieve_payment))
        .route("/payments/:payment_id/confirm", post(confirm_payment))
        .route("/payments/:payment_id/cancel", post(cancel_payment))
        .route("/payments/:payment_id/cancel_post_capture", post(cancel_post_capture))
        .route("/payments/:payment_id/capture", post(capture_payment))
        .route("/payments/:payment_id/incremental_authorization", post(incremental_authorization))
        .route("/payments/:payment_id/extend_authorization", post(extend_authorization))
        .route("/payments/:payment_id/3ds/authentication", post(external_3ds))
        .route("/payments/:payment_id/complete_authorize", post(complete_authorize))
        .route("/payments/:payment_id/update_metadata", post(update_metadata))
        .route("/payments/:payment_id/eligibility", post(submit_eligibility))
        .route("/payment_links/:link_id", get(payment_link_retrieve))
        .route("/payment_method_sessions", post(payment_method_sessions))
        .route("/api_keys/:merchant_id", post(create_api_key))
        .with_state(Arc::new(state));

    let port = env_u64("PAYMENTS_PORT", 9000) as u16;
    let addr = SocketAddr::from(([0, 0, 0, 0], port));
    info!("payments_service_listening on {}", addr);
    axum::serve(tokio::net::TcpListener::bind(addr).await.map_err(|e| ApiError::HttpError(e.to_string()))?, app)
        .await
        .map_err(|e| ApiError::HttpError(e.to_string()))
}
