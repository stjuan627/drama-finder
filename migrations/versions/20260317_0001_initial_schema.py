"""Initial schema."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "20260317_0001"
down_revision = None
branch_labels = None
depends_on = None


job_status = sa.Enum("queued", "running", "failed", "completed", name="jobstatus")
job_stage = sa.Enum(
    "manifest",
    "audio_extraction",
    "asr",
    "shot_detection",
    "frame_extraction",
    "representative_frames",
    "scene_merge",
    "embeddings",
    "persist",
    name="jobstage",
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "series",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("series_id", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("season_label", sa.String(length=128), nullable=True),
        sa.Column("language", sa.String(length=32), nullable=False),
        sa.Column("manifest_path", sa.String(length=1024), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("series_id"),
    )
    op.create_index("ix_series_series_id", "series", ["series_id"], unique=False)

    op.create_table(
        "episodes",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column(
            "series_pk",
            sa.UUID(),
            sa.ForeignKey("series.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("episode_id", sa.String(length=128), nullable=False),
        sa.Column("episode_no", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("video_path", sa.String(length=1024), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "series_pk",
            "episode_id",
            name="uq_episodes_series_pk_episode_id",
        ),
        sa.UniqueConstraint(
            "series_pk",
            "episode_no",
            name="uq_episodes_series_pk_episode_no",
        ),
    )
    op.create_index("ix_episodes_series_pk", "episodes", ["series_pk"], unique=False)

    op.create_table(
        "ingest_jobs",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column(
            "series_pk",
            sa.UUID(),
            sa.ForeignKey("series.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "episode_pk",
            sa.UUID(),
            sa.ForeignKey("episodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("manifest_path", sa.String(length=1024), nullable=False),
        sa.Column("status", job_status, nullable=False),
        sa.Column("current_stage", job_stage, nullable=True),
        sa.Column("progress_current", sa.Integer(), nullable=False),
        sa.Column("progress_total", sa.Integer(), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("artifacts", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_ingest_jobs_series_pk", "ingest_jobs", ["series_pk"], unique=False)
    op.create_index("ix_ingest_jobs_episode_pk", "ingest_jobs", ["episode_pk"], unique=False)

    op.create_table(
        "shots",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column(
            "episode_pk",
            sa.UUID(),
            sa.ForeignKey("episodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("shot_index", sa.Integer(), nullable=False),
        sa.Column("start_ts", sa.Float(), nullable=False),
        sa.Column("end_ts", sa.Float(), nullable=False),
        sa.Column("representative_frame_paths", sa.JSON(), nullable=False),
        sa.Column("raw_metadata", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_shots_episode_pk", "shots", ["episode_pk"], unique=False)

    op.create_table(
        "scenes",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column(
            "episode_pk",
            sa.UUID(),
            sa.ForeignKey("episodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("scene_index", sa.Integer(), nullable=False),
        sa.Column("start_ts", sa.Float(), nullable=False),
        sa.Column("end_ts", sa.Float(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("asr_text", sa.Text(), nullable=False),
        sa.Column("representative_frame_paths", sa.JSON(), nullable=False),
        sa.Column("raw_metadata", sa.JSON(), nullable=False),
        sa.Column("embedding", Vector(3072), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_scenes_episode_pk", "scenes", ["episode_pk"], unique=False)

    op.create_table(
        "frames",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column(
            "episode_pk",
            sa.UUID(),
            sa.ForeignKey("episodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "shot_pk",
            sa.UUID(),
            sa.ForeignKey("shots.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "scene_pk",
            sa.UUID(),
            sa.ForeignKey("scenes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("frame_index", sa.Integer(), nullable=False),
        sa.Column("frame_ts", sa.Float(), nullable=False),
        sa.Column("image_path", sa.String(length=1024), nullable=False),
        sa.Column("context_asr_text", sa.Text(), nullable=False),
        sa.Column("raw_metadata", sa.JSON(), nullable=False),
        sa.Column("embedding", Vector(3072), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_frames_episode_pk", "frames", ["episode_pk"], unique=False)
    op.create_index("ix_frames_shot_pk", "frames", ["shot_pk"], unique=False)
    op.create_index("ix_frames_scene_pk", "frames", ["scene_pk"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_frames_scene_pk", table_name="frames")
    op.drop_index("ix_frames_shot_pk", table_name="frames")
    op.drop_index("ix_frames_episode_pk", table_name="frames")
    op.drop_table("frames")

    op.drop_index("ix_scenes_episode_pk", table_name="scenes")
    op.drop_table("scenes")

    op.drop_index("ix_shots_episode_pk", table_name="shots")
    op.drop_table("shots")

    op.drop_index("ix_ingest_jobs_episode_pk", table_name="ingest_jobs")
    op.drop_index("ix_ingest_jobs_series_pk", table_name="ingest_jobs")
    op.drop_table("ingest_jobs")

    op.drop_index("ix_episodes_series_pk", table_name="episodes")
    op.drop_table("episodes")

    op.drop_index("ix_series_series_id", table_name="series")
    op.drop_table("series")
