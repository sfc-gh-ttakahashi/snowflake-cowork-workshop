-- =============================================================
-- load.sql - Git 連携の作成
-- 新規 SQL ファイルに貼り付けて「すべて実行」してください。
-- 実行後、Workspaces の「From Git repository」で
-- https://github.com/sfc-gh-ttakahashi/snowflake-cowork-workshop を開きます。
-- =============================================================
USE ROLE ACCOUNTADMIN;

CREATE DATABASE IF NOT EXISTS COWORK_HANDSON_GIT_DB
    COMMENT = 'CoWork ハンズオン: Git 連携用';
CREATE SCHEMA IF NOT EXISTS COWORK_HANDSON_GIT_DB.GIT
    COMMENT = 'CoWork ハンズオン: Git リポジトリ';
USE SCHEMA COWORK_HANDSON_GIT_DB.GIT;

-- 公開リポジトリなので認証情報（SECRET）は不要
CREATE OR REPLACE API INTEGRATION cowork_handson_git_integration
    API_PROVIDER         = git_https_api
    API_ALLOWED_PREFIXES = ('https://github.com/sfc-gh-ttakahashi/')
    ENABLED              = TRUE
    COMMENT              = 'CoWork ハンズオン: GitHub 連携';

CREATE OR REPLACE GIT REPOSITORY cowork_handson_git_repo
    API_INTEGRATION = cowork_handson_git_integration
    ORIGIN          = 'https://github.com/sfc-gh-ttakahashi/snowflake-cowork-workshop.git'
    COMMENT         = 'CoWork ハンズオン資材';

ALTER GIT REPOSITORY cowork_handson_git_repo FETCH;

-- ファイルが見えれば成功
LS @cowork_handson_git_repo/branches/main/;
