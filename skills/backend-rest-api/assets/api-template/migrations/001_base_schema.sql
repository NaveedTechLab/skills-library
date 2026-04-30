-- Base schema with soft delete, audit columns, and JWT refresh tokens

CREATE TABLE users (
  id            BIGSERIAL PRIMARY KEY,
  email         TEXT        NOT NULL UNIQUE,
  password_hash TEXT        NOT NULL,
  name          TEXT        NOT NULL,
  role          TEXT        NOT NULL DEFAULT 'user'
                  CHECK (role IN ('user', 'admin')),
  deleted_at    TIMESTAMPTZ,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users (email) WHERE deleted_at IS NULL;

CREATE TABLE resources (
  id          BIGSERIAL PRIMARY KEY,
  user_id     BIGINT      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name        TEXT        NOT NULL CHECK (length(name) > 0),
  description TEXT,
  status      TEXT        NOT NULL DEFAULT 'draft'
                CHECK (status IN ('draft', 'active', 'archived')),
  deleted_at  TIMESTAMPTZ,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_resources_user   ON resources (user_id, created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX idx_resources_status ON resources (status) WHERE deleted_at IS NULL;

CREATE TABLE refresh_tokens (
  id          BIGSERIAL PRIMARY KEY,
  user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash  TEXT   NOT NULL UNIQUE,
  expires_at  TIMESTAMPTZ NOT NULL,
  revoked_at  TIMESTAMPTZ,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_refresh_tokens_user ON refresh_tokens (user_id) WHERE revoked_at IS NULL;

-- Automatically maintain updated_at
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$;

CREATE TRIGGER trg_users_updated_at     BEFORE UPDATE ON users     FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_resources_updated_at BEFORE UPDATE ON resources FOR EACH ROW EXECUTE FUNCTION set_updated_at();
