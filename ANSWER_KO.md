# ai4pkm_cli.json 파일 위치 안내

## 질문: ai4pkm_cli.json 파일은 어디에 있나요?

### 답변

`ai4pkm_cli.json` 파일은 **vault 디렉토리 안**에 위치해야 합니다.

**올바른 위치:** `ai4pkm_vault/ai4pkm_cli.json`

### 초기 설정 방법

1. **예제 설정 파일 복사:**
   ```bash
   cp ai4pkm_cli.json.example ai4pkm_vault/ai4pkm_cli.json
   ```

2. **vault 디렉토리로 이동:**
   ```bash
   cd ai4pkm_vault
   ```

3. **CLI 실행하여 설정 확인:**
   ```bash
   ai4pkm --show-config
   ```

### 왜 이 위치인가요?

AI4PKM CLI는 Obsidian vault와 함께 작동하도록 설계되었습니다. `ai4pkm` 명령을 실행하면 CLI는:
1. 현재 작업 디렉토리에서 `ai4pkm_cli.json` 파일을 찾습니다
2. vault 디렉토리 안에서 실행되기를 기대합니다
3. JSON 파일에 설정된 상대 경로를 vault 루트 기준으로 사용합니다

### 중요한 사항

**항상 vault 디렉토리에서 CLI를 실행하세요:**
```bash
cd ai4pkm_vault
ai4pkm
```

### 문제 해결

**오류: "ai4pkm_cli.json not found"**

**원인:** 잘못된 디렉토리에서 CLI를 실행하고 있습니다.

**해결방법:**
1. `ai4pkm_cli.json` 파일이 vault 디렉토리에 있는지 확인
2. vault로 이동: `cd ai4pkm_vault`
3. 그곳에서 CLI 실행: `ai4pkm`

### 더 자세한 정보

영문 문서를 참조하세요:
- [CONFIG.md](CONFIG.md) - 전체 설정 가이드
- [docs/cli_tool.md](docs/cli_tool.md) - CLI 도구 문서
- [README.md](README.md) - 빠른 시작 가이드

### 설정 파일 예제

Repository root에 `ai4pkm_cli.json.example` 파일이 제공됩니다. 이 파일을 vault 디렉토리로 복사하여 사용하면 됩니다.

```bash
# 예제 파일 복사
cp ai4pkm_cli.json.example ai4pkm_vault/ai4pkm_cli.json

# 필요에 따라 편집
cd ai4pkm_vault
vi ai4pkm_cli.json  # 또는 원하는 에디터 사용
```
