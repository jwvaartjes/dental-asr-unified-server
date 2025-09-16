# Dental ASR System - Project Overview

## Purpose
A unified real-time dental speech recognition system with advanced normalization and file transcription. Built specifically for Dutch dental practices, featuring OpenAI GPT-4o-transcribe integration, custom dental terminology normalization, and complete pairing server infrastructure.

## Key Features
- **Unified Server Architecture**: Single server on port 8089 handles ALL functionality
- **OpenAI GPT-4o-transcribe**: State-of-the-art ASR with dental-specific prompts
- **File Upload Transcription**: Upload audio files for transcription with validation
- **Real-time WebSocket**: Live audio streaming and device pairing
- **Dental Normalization**: Specialized for Dutch dental terminology
- **Device Pairing**: Desktop-mobile pairing system for remote audio capture
- **Supabase Cloud Storage**: Per-user lexicons and configurations (REQUIRED)
- **Complete API Suite**: REST endpoints for all operations
- **Comprehensive Testing**: Built-in test pages for all functionality

## Current State
The system is in active development with a working unified server architecture. Recent focus has been on fixing normalization pipeline issues, particularly around hyphenated dental terms like 'peri-apicaal'.

## Architecture Overview
- **Main Server**: FastAPI application on port 8089 (unified architecture)
- **Modules**: Pairing, AI/ASR, Lexicon, Authentication, Data layers
- **Storage**: Supabase for user data, lexicons, configurations
- **Testing**: Extensive test suite with HTML test pages

## Recent Work
- **PERIAPICAAL HYPHEN PRESERVATION FIX**: Partially fixed issue where canonical hyphenated dental terms like 'peri-apicaal' were losing their hyphens during normalization
- **Unit Protection**: Time unit protection in normalization pipeline
- **Primary Teeth Support**: Added validation for tooth number parsing