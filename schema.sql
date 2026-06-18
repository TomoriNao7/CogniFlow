-- ============================================================================
-- CogniFlow 电商智能客服 — 数据库建表脚本
-- 数据库：PostgreSQL 15+
-- 编码：UTF-8
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. model_registry — 模型注册表
-- ============================================================================
CREATE TABLE model_registry (
    id                  SERIAL PRIMARY KEY,
    model_name          VARCHAR(64) NOT NULL UNIQUE,
    provider            VARCHAR(32) NOT NULL,
    display_name        VARCHAR(128),
    endpoint_url        VARCHAR(512) NOT NULL,
    api_key_ref         VARCHAR(128) NOT NULL,
    context_window      INTEGER,
    max_tokens          INTEGER,
    pricing_tier        VARCHAR(16),
    cost_per_1k_input   NUMERIC(10,6),
    cost_per_1k_output  NUMERIC(10,6),
    status              VARCHAR(16) DEFAULT 'active',
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW(),
    deleted_at          TIMESTAMP
);

CREATE INDEX idx_mr_active ON model_registry(deleted_at) WHERE deleted_at IS NULL;

INSERT INTO model_registry (model_name, provider, display_name, endpoint_url, api_key_ref, context_window, max_tokens, pricing_tier) VALUES
  ('qwen-max',      'qwen', '通义千问 Max',  'https://dashscope.aliyuncs.com/compatible-mode/v1', 'QWEN_API_KEY', 32768, 4096, 'premium'),
  ('qwen-plus',     'qwen', '通义千问 Plus', 'https://dashscope.aliyuncs.com/compatible-mode/v1', 'QWEN_API_KEY', 32768, 4096, 'standard'),
  ('qwen-turbo',    'qwen', '通义千问 Turbo','https://dashscope.aliyuncs.com/compatible-mode/v1', 'QWEN_API_KEY', 32768, 4096, 'budget'),
  ('qwen2.5-1.5b',  'qwen', '通义千问 1.5B', 'https://dashscope.aliyuncs.com/compatible-mode/v1', 'QWEN_API_KEY', 32768, 2048, 'budget');

-- ============================================================================
-- 2. content_safety_rules — 内容安全规则表
-- ============================================================================
CREATE TABLE content_safety_rules (
    id              SERIAL PRIMARY KEY,
    rule_type       VARCHAR(32) NOT NULL,
    pattern         TEXT NOT NULL,
    severity        VARCHAR(16) NOT NULL,
    action          VARCHAR(16) NOT NULL,
    description     VARCHAR(256),
    is_active       BOOLEAN DEFAULT TRUE,
    hit_count       INTEGER DEFAULT 0,
    last_hit_at     TIMESTAMP,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),
    deleted_at      TIMESTAMP
);

CREATE INDEX idx_csr_severity ON content_safety_rules(severity);
CREATE INDEX idx_csr_active   ON content_safety_rules(deleted_at) WHERE deleted_at IS NULL;

INSERT INTO content_safety_rules (rule_type, pattern, severity, action, description) VALUES
  ('regex',   '\b\d{15,19}\b',           'severe',   'silent_block', '疑似银行卡号'),
  ('regex',   '\b1[3-9]\d{9}\b',         'moderate', 'block',        '手机号（需脱敏后放行）'),
  ('keyword', '管理员密码',                'severe',   'silent_block', '越狱探测'),
  ('keyword', '忽略之前的指令',             'severe',   'silent_block', '提示词注入探测'),
  ('keyword', '傻逼',                      'moderate', 'block',        '侮辱性语言'),
  ('semantic','威胁客服人员',               'severe',   'silent_block', '人身威胁');

-- ============================================================================
-- 3. admin_users — 管理员表
-- ============================================================================
CREATE TABLE admin_users (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR(64) NOT NULL UNIQUE,
    password_hash   VARCHAR(256) NOT NULL,          -- bcrypt(cost=12) 哈希
    role            VARCHAR(32) DEFAULT 'operator',
    status          VARCHAR(16) DEFAULT 'active',
    last_login_at   TIMESTAMP,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),
    deleted_at      TIMESTAMP
);

CREATE INDEX idx_au_active ON admin_users(deleted_at) WHERE deleted_at IS NULL;

-- ============================================================================
-- 4. agents — Agent 表
-- ============================================================================
CREATE TABLE agents (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(64) NOT NULL UNIQUE,
    display_name    VARCHAR(128),
    model           VARCHAR(32) NOT NULL,            -- 引用 model_registry.model_name
    system_prompt   TEXT,
    status          VARCHAR(16) DEFAULT 'active',
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),
    deleted_at      TIMESTAMP
);

CREATE INDEX idx_agents_active ON agents(deleted_at) WHERE deleted_at IS NULL;

INSERT INTO agents (name, display_name, model) VALUES
  ('pre_sales',    '售前客服', 'qwen-max'),
  ('during_sales', '售中客服', 'qwen-plus'),
  ('after_sales',  '售后客服', 'qwen-max');

-- ============================================================================
-- 5. agent_retrieval_params — Agent 检索参数表
-- ============================================================================
CREATE TABLE agent_retrieval_params (
    id          SERIAL PRIMARY KEY,
    agent_id    INTEGER NOT NULL REFERENCES agents(id),
    param_key   VARCHAR(64) NOT NULL,
    param_value VARCHAR(128) NOT NULL,

    UNIQUE (agent_id, param_key)
);

CREATE INDEX idx_arp_agent_id ON agent_retrieval_params(agent_id);

INSERT INTO agent_retrieval_params (agent_id, param_key, param_value) VALUES
  (1, 'top_k',                '5'),
  (1, 'similarity_threshold', '0.75'),
  (1, 'bm25_weight',          '0.3'),
  (1, 'vector_weight',        '0.7'),
  (1, 'rerank_enabled',       'true');

-- ============================================================================
-- 6. intent_definitions — 意图定义表
-- ============================================================================
CREATE TABLE intent_definitions (
    id                  SERIAL PRIMARY KEY,
    intent_name         VARCHAR(64) NOT NULL UNIQUE,
    display_name        VARCHAR(128),
    target_agent_id     INTEGER NOT NULL REFERENCES agents(id),
    description         TEXT,
    example_utterances  TEXT,
    priority            INTEGER DEFAULT 0,
    status              VARCHAR(16) DEFAULT 'active',
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW(),
    deleted_at          TIMESTAMP
);

CREATE INDEX idx_id_target_agent ON intent_definitions(target_agent_id);
CREATE INDEX idx_id_active        ON intent_definitions(deleted_at) WHERE deleted_at IS NULL;

INSERT INTO intent_definitions (intent_name, display_name, target_agent_id, example_utterances) VALUES
  ('query_product',    '商品咨询', 1, '这个商品有货吗\n有什么颜色\n和XX比哪个好'),
  ('check_promotion',  '优惠查询', 1, '现在有什么优惠\n新人优惠券怎么领\n会员价是多少'),
  ('place_order',      '下单帮助', 2, '怎么下单\n支付不了\n地址怎么改'),
  ('invoice_request',  '申请发票', 2, '开发票\n发票信息怎么填'),
  ('check_logistics',  '查物流',   3, '我的货到哪了\n快递单号多少\n什么时候发货'),
  ('refund_request',   '申请退款', 3, '我要退款\n怎么退货\n退款什么时候到账'),
  ('complaint',        '投诉建议', 3, '我要投诉\n你们客服太差了\n商品有问题');

-- ============================================================================
-- 7. slot_definitions — 槽位定义表
-- ============================================================================
CREATE TABLE slot_definitions (
    id              SERIAL PRIMARY KEY,
    intent_name     VARCHAR(64) NOT NULL,
    slot_name       VARCHAR(64) NOT NULL,
    slot_type       VARCHAR(32) NOT NULL,
    question_prompt TEXT NOT NULL,
    validation_rule VARCHAR(256),
    is_required     BOOLEAN DEFAULT TRUE,
    sort_order      INTEGER DEFAULT 0,
    created_at      TIMESTAMP DEFAULT NOW(),

    UNIQUE (intent_name, slot_name)
);

CREATE INDEX idx_sd_intent ON slot_definitions(intent_name);

INSERT INTO slot_definitions (intent_name, slot_name, slot_type, question_prompt, validation_rule, sort_order) VALUES
  ('refund_request',  'phone',       'phone',  '请提供您的手机号，方便我查询订单', '^1[3-9]\d{9}$', 1),
  ('refund_request',  'order_id',    'string', '请问需要退款的订单号是多少？',     NULL,             2),
  ('refund_request',  'reason',      'string', '请简单描述退款原因',              NULL,             3),
  ('check_logistics', 'phone',       'phone',  '请提供您的手机号，我帮您查物流',  '^1[3-9]\d{9}$', 1),
  ('check_logistics', 'order_id',    'string', '请问您的订单号是多少？',          NULL,             2),
  ('complaint',       'phone',       'phone',  '请留一下您的手机号，方便我们联系您', '^1[3-9]\d{9}$', 1),
  ('complaint',       'reason',      'string', '请描述您遇到的问题',              NULL,             2);

-- ============================================================================
-- 8. tools — 工具表
-- ============================================================================
CREATE TABLE tools (
    id                  SERIAL PRIMARY KEY,
    name                VARCHAR(64) NOT NULL,
    display_name        VARCHAR(128),
    description         TEXT,
    endpoint_url        VARCHAR(512) NOT NULL,
    http_method         VARCHAR(8) DEFAULT 'POST',
    timeout_ms          INTEGER DEFAULT 5000,
    retry_count         INTEGER DEFAULT 2,
    auth_type           VARCHAR(32) DEFAULT 'none',
    auth_credential_ref VARCHAR(128),
    version             VARCHAR(16) DEFAULT '1.0',
    status              VARCHAR(16) DEFAULT 'active',
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW(),
    deleted_at          TIMESTAMP,

    UNIQUE (name, version)
);

CREATE INDEX idx_tools_active ON tools(deleted_at) WHERE deleted_at IS NULL;

-- ============================================================================
-- 9. tool_parameters — 工具参数表
-- ============================================================================
CREATE TABLE tool_parameters (
    id              SERIAL PRIMARY KEY,
    tool_id         INTEGER NOT NULL REFERENCES tools(id),
    param_name      VARCHAR(64) NOT NULL,
    param_type      VARCHAR(32) NOT NULL,
    param_desc      VARCHAR(256),
    is_required     BOOLEAN DEFAULT FALSE,
    default_value   VARCHAR(128),
    sort_order      INTEGER DEFAULT 0
);

CREATE INDEX idx_tp_tool_id ON tool_parameters(tool_id);

-- ============================================================================
-- 10. agent_tools — Agent-工具关联表
-- ============================================================================
CREATE TABLE agent_tools (
    id           SERIAL PRIMARY KEY,
    agent_id     INTEGER NOT NULL REFERENCES agents(id),
    tool_id      INTEGER NOT NULL REFERENCES tools(id),
    tool_version VARCHAR(16),
    created_at   TIMESTAMP DEFAULT NOW(),

    UNIQUE (agent_id, tool_id)
);

-- ============================================================================
-- 11. users — 用户表
-- ============================================================================
CREATE TABLE users (
    id            SERIAL PRIMARY KEY,
    external_id   VARCHAR(128) NOT NULL UNIQUE,
    nickname      VARCHAR(128),
    phone         VARCHAR(256) NOT NULL,             -- AES-256 加密存储
    email         VARCHAR(256),                       -- AES-256 加密存储
    created_at    TIMESTAMP DEFAULT NOW(),
    updated_at    TIMESTAMP DEFAULT NOW(),
    deleted_at    TIMESTAMP
);

CREATE INDEX idx_users_external_id ON users(external_id);
CREATE INDEX idx_users_active      ON users(deleted_at) WHERE deleted_at IS NULL;

-- ============================================================================
-- 12. user_attributes — 用户属性表
-- ============================================================================
CREATE TABLE user_attributes (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    attr_key    VARCHAR(64) NOT NULL,
    attr_value  VARCHAR(256) NOT NULL,
    created_at  TIMESTAMP DEFAULT NOW(),

    UNIQUE (user_id, attr_key)
);

CREATE INDEX idx_ua_user_id ON user_attributes(user_id);

-- ============================================================================
-- 13. user_tags — 用户标签表
-- ============================================================================
CREATE TABLE user_tags (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    tag         VARCHAR(64) NOT NULL,
    created_at  TIMESTAMP DEFAULT NOW(),

    UNIQUE (user_id, tag)
);

CREATE INDEX idx_ut_user_id ON user_tags(user_id);

-- ============================================================================
-- 14. conversations — 会话表
-- ============================================================================
CREATE TABLE conversations (
    id               SERIAL PRIMARY KEY,
    user_id          INTEGER NOT NULL REFERENCES users(id),
    agent_id         INTEGER REFERENCES agents(id),
    status           VARCHAR(16) DEFAULT 'active',
    title            VARCHAR(256),
    source           VARCHAR(32) DEFAULT 'widget',
    last_message_at  TIMESTAMP,
    created_at       TIMESTAMP DEFAULT NOW(),
    updated_at       TIMESTAMP DEFAULT NOW(),
    deleted_at       TIMESTAMP
);

CREATE INDEX idx_conv_user_id       ON conversations(user_id);
CREATE INDEX idx_conv_status        ON conversations(status);
CREATE INDEX idx_conv_agent_id      ON conversations(agent_id);
CREATE INDEX idx_conv_created_at    ON conversations(created_at);
CREATE INDEX idx_conv_last_msg      ON conversations(last_message_at);
CREATE INDEX idx_conv_active        ON conversations(deleted_at) WHERE deleted_at IS NULL;

-- ============================================================================
-- 15. messages — 消息表
-- ============================================================================
CREATE TABLE messages (
    id              SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id),
    role            VARCHAR(8) NOT NULL,
    content         TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_msg_conv_id    ON messages(conversation_id);
CREATE INDEX idx_msg_created_at ON messages(conversation_id, created_at);

-- ============================================================================
-- 16. message_traces — 消息追踪表
-- ============================================================================
CREATE TABLE message_traces (
    id                           SERIAL PRIMARY KEY,
    message_id                   INTEGER NOT NULL UNIQUE REFERENCES messages(id),

    -- 意图分类
    intent_agent                 VARCHAR(64),
    intent_confidence            DECIMAL(4,3),
    intent_duration_ms           INTEGER,

    -- 检索
    retrieval_query              TEXT,
    retrieval_recalled_count     INTEGER,
    retrieval_top_k              INTEGER,
    retrieval_duration_ms        INTEGER,

    -- 重排序
    rerank_model                 VARCHAR(64),
    rerank_duration_ms           INTEGER,

    -- 生成
    generation_model             VARCHAR(32),
    generation_prompt_tokens     INTEGER,
    generation_completion_tokens INTEGER,
    generation_ttft_ms           INTEGER,
    generation_duration_ms       INTEGER,

    created_at                   TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_mt_message_id ON message_traces(message_id);

-- ============================================================================
-- 17. trace_retrieval_chunks — 检索结果明细表
-- ============================================================================
CREATE TABLE trace_retrieval_chunks (
    id              SERIAL PRIMARY KEY,
    trace_id        INTEGER NOT NULL REFERENCES message_traces(id),
    document_id     INTEGER NOT NULL REFERENCES knowledge_documents(id) DEFERRABLE,
    chunk_id        INTEGER NOT NULL REFERENCES knowledge_chunks(id) DEFERRABLE,
    score           DECIMAL(6,4) NOT NULL,
    rank_position   INTEGER NOT NULL
);

CREATE INDEX idx_trc_trace_id ON trace_retrieval_chunks(trace_id);

-- ============================================================================
-- 18. trace_function_calls — 工具调用明细表
-- ============================================================================
CREATE TABLE trace_function_calls (
    id              SERIAL PRIMARY KEY,
    trace_id        INTEGER NOT NULL REFERENCES message_traces(id),
    tool_name       VARCHAR(64) NOT NULL,
    tool_version    VARCHAR(16),
    parameters      TEXT,
    is_success      BOOLEAN NOT NULL,
    result_summary  TEXT,
    attempt_index   INTEGER DEFAULT 0,
    duration_ms     INTEGER,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_tfc_trace_id ON trace_function_calls(trace_id);

-- ============================================================================
-- 19. knowledge_documents — 知识文档表
-- ============================================================================
CREATE TABLE knowledge_documents (
    id                SERIAL PRIMARY KEY,
    title             VARCHAR(256) NOT NULL,
    file_type         VARCHAR(16) NOT NULL,
    split_method      VARCHAR(32) NOT NULL,
    file_path         VARCHAR(512),
    original_filename VARCHAR(256),
    file_size_bytes   BIGINT,
    uploaded_by       INTEGER REFERENCES admin_users(id),
    version           INTEGER DEFAULT 1,
    status            VARCHAR(16) DEFAULT 'active',
    created_at        TIMESTAMP DEFAULT NOW(),
    updated_at        TIMESTAMP DEFAULT NOW(),
    deleted_at        TIMESTAMP
);

CREATE INDEX idx_kd_file_type ON knowledge_documents(file_type);
CREATE INDEX idx_kd_status    ON knowledge_documents(status);
CREATE INDEX idx_kd_active    ON knowledge_documents(deleted_at) WHERE deleted_at IS NULL;

-- ============================================================================
-- 20. knowledge_chunks — 知识切片表
-- ============================================================================
CREATE TABLE knowledge_chunks (
    id                SERIAL PRIMARY KEY,
    document_id       INTEGER NOT NULL REFERENCES knowledge_documents(id),
    chunk_index       INTEGER NOT NULL,
    content           TEXT NOT NULL,
    retrieval_count   INTEGER DEFAULT 0,
    last_retrieved_at TIMESTAMP,
    created_at        TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_kc_document_id ON knowledge_chunks(document_id);

-- ============================================================================
-- 21. chunk_metadata — 切片元信息表
-- ============================================================================
CREATE TABLE chunk_metadata (
    id          SERIAL PRIMARY KEY,
    chunk_id    INTEGER NOT NULL REFERENCES knowledge_chunks(id),
    meta_key    VARCHAR(64) NOT NULL,
    meta_value  VARCHAR(512),

    UNIQUE (chunk_id, meta_key)
);

CREATE INDEX idx_cm_chunk_id ON chunk_metadata(chunk_id);

-- ============================================================================
-- 22. chunk_tags — 切片标签表
-- ============================================================================
CREATE TABLE chunk_tags (
    id          SERIAL PRIMARY KEY,
    chunk_id    INTEGER NOT NULL REFERENCES knowledge_chunks(id),
    tag         VARCHAR(128) NOT NULL,

    UNIQUE (chunk_id, tag)
);

CREATE INDEX idx_ct_chunk_id ON chunk_tags(chunk_id);

-- ============================================================================
-- 23. document_processing_jobs — 文档处理任务表
-- ============================================================================
CREATE TABLE document_processing_jobs (
    id                SERIAL PRIMARY KEY,
    document_id       INTEGER NOT NULL REFERENCES knowledge_documents(id),
    job_type          VARCHAR(32) NOT NULL,
    status            VARCHAR(16) DEFAULT 'pending',
    progress_pct      INTEGER DEFAULT 0,
    total_chunks      INTEGER,
    completed_chunks  INTEGER DEFAULT 0,
    error_message     TEXT,
    started_at        TIMESTAMP,
    completed_at      TIMESTAMP,
    created_at        TIMESTAMP DEFAULT NOW(),
    updated_at        TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_dpj_document_id ON document_processing_jobs(document_id);
CREATE INDEX idx_dpj_status      ON document_processing_jobs(status);

-- ============================================================================
-- 24. feedbacks — 反馈表
-- ============================================================================
CREATE TABLE feedbacks (
    id              SERIAL PRIMARY KEY,
    message_id      INTEGER NOT NULL REFERENCES messages(id),
    rating          VARCHAR(16) NOT NULL,
    reason          TEXT,
    reviewed_by     INTEGER REFERENCES admin_users(id),
    reviewed_at     TIMESTAMP,
    review_status   VARCHAR(16) DEFAULT 'pending',
    created_at      TIMESTAMP DEFAULT NOW(),
    deleted_at      TIMESTAMP
);

CREATE INDEX idx_fb_message_id ON feedbacks(message_id);
CREATE INDEX idx_fb_active      ON feedbacks(deleted_at) WHERE deleted_at IS NULL;

-- ============================================================================
-- 25. human_handoffs — 转人工记录表
-- ============================================================================
CREATE TABLE human_handoffs (
    id                SERIAL PRIMARY KEY,
    conversation_id   INTEGER NOT NULL REFERENCES conversations(id),
    reason            VARCHAR(64) NOT NULL,
    summary           TEXT,
    intent_agent      VARCHAR(64),
    status            VARCHAR(16) DEFAULT 'pending',
    claimed_by        INTEGER REFERENCES admin_users(id),
    resolution_note   TEXT,
    created_at        TIMESTAMP DEFAULT NOW(),
    resolved_at       TIMESTAMP,
    deleted_at        TIMESTAMP
);

CREATE INDEX idx_hh_status ON human_handoffs(status);
CREATE INDEX idx_hh_active ON human_handoffs(deleted_at) WHERE deleted_at IS NULL;

-- ============================================================================
-- 26. handoff_slots — 转交槽位信息表
-- ============================================================================
CREATE TABLE handoff_slots (
    id              SERIAL PRIMARY KEY,
    handoff_id      INTEGER NOT NULL REFERENCES human_handoffs(id),
    slot_name       VARCHAR(64) NOT NULL,
    slot_value      VARCHAR(256),

    UNIQUE (handoff_id, slot_name)
);

CREATE INDEX idx_hs_handoff_id ON handoff_slots(handoff_id);

-- ============================================================================
-- 27. handoff_agent_attempts — 转交 Agent 尝试记录表
-- ============================================================================
CREATE TABLE handoff_agent_attempts (
    id              SERIAL PRIMARY KEY,
    handoff_id      INTEGER NOT NULL REFERENCES human_handoffs(id),
    tool_name       VARCHAR(64) NOT NULL,
    attempt_index   INTEGER NOT NULL,
    result          VARCHAR(128) NOT NULL,
    error_detail    TEXT,

    UNIQUE (handoff_id, attempt_index)
);

CREATE INDEX idx_haa_handoff_id ON handoff_agent_attempts(handoff_id);

-- ============================================================================
-- 28. evaluation_runs — 评估运行表
-- ============================================================================
CREATE TABLE evaluation_runs (
    id                      SERIAL PRIMARY KEY,
    name                    VARCHAR(256) NOT NULL,
    agent_id                INTEGER REFERENCES agents(id),
    test_set_name           VARCHAR(256),
    total_cases             INTEGER,
    completed_cases         INTEGER DEFAULT 0,
    intent_accuracy         NUMERIC(5,2),
    retrieval_hit_rate      NUMERIC(5,2),
    retrieval_recall        NUMERIC(5,2),
    retrieval_precision     NUMERIC(5,2),
    retrieval_mrr           NUMERIC(5,4),
    tool_call_accuracy      NUMERIC(5,2),
    generation_accuracy     NUMERIC(5,2),
    hallucination_rate      NUMERIC(5,2),
    avg_ttft_ms             INTEGER,
    avg_total_duration_ms   INTEGER,
    status                  VARCHAR(16) DEFAULT 'pending',
    created_by              INTEGER REFERENCES admin_users(id),
    created_at              TIMESTAMP DEFAULT NOW(),
    completed_at            TIMESTAMP
);

CREATE INDEX idx_er_agent_id ON evaluation_runs(agent_id);
CREATE INDEX idx_er_status   ON evaluation_runs(status);

-- ============================================================================
-- 29. evaluation_results — 评估结果明细表
-- ============================================================================
CREATE TABLE evaluation_results (
    id                  SERIAL PRIMARY KEY,
    run_id              INTEGER NOT NULL REFERENCES evaluation_runs(id),
    case_index          INTEGER NOT NULL,
    question            TEXT NOT NULL,
    expected_intent     VARCHAR(64),
    actual_intent       VARCHAR(64),
    intent_correct      BOOLEAN,
    expected_tool       VARCHAR(64),
    actual_tool         VARCHAR(64),
    tool_correct        BOOLEAN,
    retrieval_hit       BOOLEAN,
    retrieval_recall    NUMERIC(5,2),
    retrieval_precision NUMERIC(5,2),
    generation_score    NUMERIC(5,2),
    hallucination       BOOLEAN,
    actual_answer       TEXT,
    expected_answer     TEXT,
    ttft_ms             INTEGER,
    total_duration_ms   INTEGER,
    created_at          TIMESTAMP DEFAULT NOW(),

    UNIQUE (run_id, case_index)
);

CREATE INDEX idx_eres_run_id ON evaluation_results(run_id);

-- ============================================================================
-- 30. audit_log — 审计日志表
-- ============================================================================
CREATE TABLE audit_log (
    id              BIGSERIAL PRIMARY KEY,
    admin_user_id   INTEGER REFERENCES admin_users(id),
    action          VARCHAR(64) NOT NULL,
    entity_type     VARCHAR(64) NOT NULL,
    entity_id       INTEGER,
    summary         VARCHAR(512),
    detail          TEXT,
    ip_address      VARCHAR(45),
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_al_admin_user ON audit_log(admin_user_id);
CREATE INDEX idx_al_entity      ON audit_log(entity_type, entity_id);
CREATE INDEX idx_al_created_at  ON audit_log(created_at);

-- ============================================================================
-- 视图
-- ============================================================================
-- 31. knowledge_document_stats — 知识文档统计视图
-- ============================================================================
CREATE VIEW knowledge_document_stats AS
SELECT
    d.id,
    d.title,
    COUNT(c.id)                              AS chunk_count,
    COALESCE(SUM(c.retrieval_count), 0)      AS total_retrievals
FROM knowledge_documents d
LEFT JOIN knowledge_chunks c ON c.document_id = d.id
WHERE d.deleted_at IS NULL
GROUP BY d.id, d.title;

-- ============================================================================
-- 32. conversation_satisfaction — 会话满意度视图
-- ============================================================================
CREATE VIEW conversation_satisfaction AS
SELECT
    c.id AS conversation_id,
    f.rating,
    f.reason,
    f.created_at
FROM conversations c
JOIN messages m ON m.conversation_id = c.id
JOIN feedbacks f ON f.message_id = m.id
WHERE c.deleted_at IS NULL
  AND f.deleted_at IS NULL;

-- ============================================================================
-- 完成
-- ============================================================================
COMMIT;
