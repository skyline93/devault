---
sidebar_position: 4
title: 发版与变更记录
description: 版本号与 CHANGELOG 约定
---

# 发版与变更记录

## 版本号

Python 包版本在 **`pyproject.toml`** 的 `[project]` → `version` 字段维护。

## CHANGELOG

人类可读的变更摘要写在仓库根 **`CHANGELOG.md`**。建议遵循 [Keep a Changelog](https://keepachangelog.com/) 风格，与 tag 或发版节奏对齐。

## 文档站

用户面向的说明性改动应同步更新 **`website/docs/`** 下对应页面，避免仅更新 README 或 CHANGELOG 之一。
