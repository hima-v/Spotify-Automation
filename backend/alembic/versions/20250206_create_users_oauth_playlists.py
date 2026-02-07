"""Create users, oauth_tokens, playlist_configs, playlist_runs

Revision ID: 20250206_01
Revises:
Create Date: 2025-02-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250206_01"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("spotify_user_id", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_spotify_user_id", "users", ["spotify_user_id"], unique=True)

    op.create_table(
        "oauth_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scope", sa.String(512), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_oauth_tokens_user_id", "oauth_tokens", ["user_id"], unique=False)

    op.create_table(
        "playlist_configs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("source_playlist_id", sa.String(255), nullable=False),
        sa.Column("target_playlist_id", sa.String(255), nullable=False),
        sa.Column("strategy_json", sa.JSON(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_playlist_configs_user_id", "playlist_configs", ["user_id"], unique=False)

    op.create_table(
        "playlist_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("playlist_config_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tracks_added_count", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["playlist_config_id"], ["playlist_configs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_playlist_runs_playlist_config_id", "playlist_runs", ["playlist_config_id"], unique=False)
    op.create_index("ix_playlist_runs_config_started", "playlist_runs", ["playlist_config_id", "started_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_playlist_runs_config_started", table_name="playlist_runs")
    op.drop_index("ix_playlist_runs_playlist_config_id", table_name="playlist_runs")
    op.drop_table("playlist_runs")
    op.drop_index("ix_playlist_configs_user_id", table_name="playlist_configs")
    op.drop_table("playlist_configs")
    op.drop_index("ix_oauth_tokens_user_id", table_name="oauth_tokens")
    op.drop_table("oauth_tokens")
    op.drop_index("ix_users_spotify_user_id", table_name="users")
    op.drop_table("users")
