-- =============================================================
-- cleanup.sql - ハンズオンで作成したオブジェクトの削除
-- トライアルのクレジットを残したい場合に実行してください。
-- =============================================================
USE ROLE ACCOUNTADMIN;

-- CoWork から Agent を外してから削除する
ALTER SNOWFLAKE INTELLIGENCE SNOWFLAKE_INTELLIGENCE_OBJECT_DEFAULT
    DROP AGENT COWORK_HANDSON_DB.ANALYTICS.mfg_agent;

DROP DATABASE IF EXISTS COWORK_HANDSON_DB;
DROP DATABASE IF EXISTS COWORK_HANDSON_GIT_DB;
DROP WAREHOUSE IF EXISTS COWORK_HANDSON_WH;
DROP API INTEGRATION IF EXISTS cowork_handson_git_integration;
