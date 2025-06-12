# AI自動化ツール改善計画書

## 1. 現状分析

### 1.1 現在の実装概要
- **技術スタック**: Playwright + Python + Tkinter GUI
- **対象AIツール**: ChatGPT、Claude、Gemini、Genspark、Google AI Studio
- **処理フロー**: スプレッドシート読み取り → ブラウザ自動操作 → 結果書き戻し

### 1.2 主要な課題

#### 1.2.1 認証・ログイン関連
- 各AIサイトへの手動ログインが必要（自動化の最大のボトルネック）
- Chromeプロファイルを使用しているが、セッション管理が不安定
- MFA（多要素認証）への対応が困難

#### 1.2.2 安定性・保守性
- UIセレクターの変更に脆弱（サイト更新で動作不能になる）
- エラー処理が複雑で、リトライロジックが煩雑
- ネットワークエラー発生率が高い（40%）

#### 1.2.3 パフォーマンス
- ブラウザ操作のため処理速度が遅い
- 並列処理が困難（ブラウザリソースの制約）
- スケーラビリティの問題

## 2. Playwright MCPを活用した改善案

### 2.1 MCP（Model Context Protocol）の導入

#### 2.1.1 実装アーキテクチャ
```python
# MCP Server実装例
from playwright_mcp_server import PlaywrightMCPServer

class AIAutomationMCPServer(PlaywrightMCPServer):
    def __init__(self):
        super().__init__()
        self.session_manager = SessionManager()
        self.ai_handlers = {
            'chatgpt': ChatGPTHandler(),
            'claude': ClaudeHandler(),
            'gemini': GeminiHandler()
        }
    
    async def execute_ai_task(self, ai_tool, prompt, settings):
        # セッション管理とエラーハンドリングを統合
        session = await self.session_manager.get_or_create_session(ai_tool)
        handler = self.ai_handlers[ai_tool]
        return await handler.process_with_session(session, prompt, settings)
```

### 2.2 セッション管理の改善

#### 2.2.1 認証状態の永続化
```python
class EnhancedSessionManager:
    def __init__(self):
        self.storage_state_dir = Path("auth_states")
        self.storage_state_dir.mkdir(exist_ok=True)
    
    async def save_auth_state(self, context, service_name):
        # 認証状態を保存（cookiesのみ、サイズ削減のため）
        state = await context.storage_state()
        # 機密情報を暗号化して保存
        encrypted_state = self.encrypt_state(state)
        state_path = self.storage_state_dir / f"{service_name}_auth.json"
        state_path.write_text(json.dumps(encrypted_state))
    
    async def restore_auth_state(self, context, service_name):
        state_path = self.storage_state_dir / f"{service_name}_auth.json"
        if state_path.exists():
            encrypted_state = json.loads(state_path.read_text())
            state = self.decrypt_state(encrypted_state)
            await context.add_cookies(state['cookies'])
            return True
        return False
```

### 2.3 より安定したセレクター戦略

#### 2.3.1 アクセシビリティベースのセレクター
```python
class SmartSelectorStrategy:
    def __init__(self):
        self.selector_fallbacks = {
            'input': [
                'role=textbox[name*="prompt"]',
                'role=textbox[name*="message"]',
                'aria-label*="Send a message"',
                'textarea[placeholder*="Send"]'
            ],
            'send': [
                'role=button[name*="Send"]',
                'aria-label*="Send message"',
                'button:has-text("Send")'
            ]
        }
    
    async def find_element(self, page, element_type):
        for selector in self.selector_fallbacks[element_type]:
            try:
                element = await page.wait_for_selector(selector, timeout=3000)
                if element:
                    return element
            except:
                continue
        return None
```

### 2.4 ネットワークレベルの最適化

#### 2.4.1 リクエストインターセプト
```python
class NetworkOptimizer:
    async def setup_interceptors(self, page):
        # 不要なリソースをブロック
        await page.route("**/*.{png,jpg,jpeg,gif,svg}", lambda route: route.abort())
        await page.route("**/analytics/**", lambda route: route.abort())
        
        # API呼び出しをインターセプト
        await page.route("**/api/**", self.handle_api_request)
    
    async def handle_api_request(self, route):
        # API呼び出しを直接処理（可能な場合）
        if self.can_handle_directly(route.request):
            response = await self.process_api_request(route.request)
            await route.fulfill(response)
        else:
            await route.continue_()
```

## 3. API直接利用への段階的移行

### 3.1 ハイブリッドアプローチ

#### 3.1.1 実装アーキテクチャ
```python
class HybridAIHandler:
    def __init__(self):
        self.api_clients = {
            'openai': OpenAIClient(),
            'anthropic': AnthropicClient(),
            'google': GoogleAIClient()
        }
        self.browser_handlers = {
            'chatgpt': ChatGPTBrowserHandler(),
            'claude': ClaudeBrowserHandler(),
            'gemini': GeminiBrowserHandler()
        }
    
    async def process_request(self, service, prompt, use_api=True):
        # APIが利用可能な場合はAPI優先
        if use_api and service in self.api_clients:
            try:
                return await self.api_clients[service].process(prompt)
            except APIError as e:
                logger.warning(f"API failed, falling back to browser: {e}")
        
        # ブラウザ自動化にフォールバック
        return await self.browser_handlers[service].process(prompt)
```

### 3.2 セキュアなAPI認証情報管理

#### 3.2.1 Keyringを使用した実装
```python
import keyring
from cryptography.fernet import Fernet

class SecureAPIManager:
    def __init__(self):
        self.service_name = "ai_automation_tool"
        self.encryption_key = self._get_or_create_encryption_key()
    
    def store_api_key(self, ai_service, api_key):
        # API keyを暗号化して保存
        encrypted_key = Fernet(self.encryption_key).encrypt(api_key.encode())
        keyring.set_password(self.service_name, f"{ai_service}_api_key", encrypted_key.decode())
    
    def get_api_key(self, ai_service):
        encrypted_key = keyring.get_password(self.service_name, f"{ai_service}_api_key")
        if encrypted_key:
            return Fernet(self.encryption_key).decrypt(encrypted_key.encode()).decode()
        return None
    
    def _get_or_create_encryption_key(self):
        key = keyring.get_password(self.service_name, "encryption_key")
        if not key:
            key = Fernet.generate_key().decode()
            keyring.set_password(self.service_name, "encryption_key", key)
        return key.encode()
```

### 3.3 API利用時のコスト最適化

#### 3.3.1 モデル選択戦略
```python
class CostOptimizedModelSelector:
    def __init__(self):
        self.model_costs = {
            'gpt-3.5-turbo': 0.002,
            'gpt-4': 0.03,
            'claude-3-sonnet': 0.003,
            'claude-3-opus': 0.015,
            'gemini-flash': 0.000075,
            'gemini-pro': 0.001
        }
    
    def select_model(self, task_complexity, budget_constraint):
        if task_complexity == 'low':
            # 軽量タスクには最も安価なモデル
            return 'gemini-flash'
        elif task_complexity == 'medium':
            # 中程度のタスクにはバランスの良いモデル
            return 'claude-3-sonnet' if budget_constraint > 0.005 else 'gpt-3.5-turbo'
        else:
            # 複雑なタスクには高性能モデル
            return 'gpt-4' if budget_constraint > 0.05 else 'claude-3-opus'
```

## 4. 段階的な実装計画

### 4.1 短期（1-2週間）

#### Phase 1: 既存実装の安定化
1. **セレクター戦略の改善**
   - アクセシビリティベースのセレクターに移行
   - フォールバック機構の実装
   - エラーログの詳細化

2. **セッション管理の強化**
   - 認証状態の永続化実装
   - セッション有効性チェック機能
   - 自動再認証メカニズム

3. **エラーハンドリングの改善**
   - 統一的なエラー分類システム
   - インテリジェントなリトライロジック
   - 詳細なエラーレポート生成

### 4.2 中期（3-4週間）

#### Phase 2: ハイブリッド実装
1. **API統合の開始**
   - OpenAI API（ChatGPT）の統合
   - Anthropic API（Claude）の統合
   - Google AI API（Gemini）の統合

2. **認証情報管理システム**
   - Keyringベースの実装
   - GUI上でのAPI key設定機能
   - 暗号化された保存

3. **切り替え機能の実装**
   - API/ブラウザの動的切り替え
   - フォールバック機構
   - パフォーマンス比較機能

### 4.3 長期（1-2ヶ月）

#### Phase 3: 完全自動化システム
1. **並列処理の実装**
   - 非同期処理の最適化
   - ワーカープールの実装
   - リソース管理システム

2. **インテリジェント処理**
   - タスクの自動分類
   - 最適なモデル自動選択
   - コスト最適化エンジン

3. **監視・分析システム**
   - リアルタイムモニタリング
   - パフォーマンス分析
   - コスト追跡とレポート

## 5. 実装の技術的詳細

### 5.1 プロジェクト構造の改善
```
src/
├── api/
│   ├── __init__.py
│   ├── base_client.py
│   ├── openai_client.py
│   ├── anthropic_client.py
│   └── google_ai_client.py
├── browser/
│   ├── __init__.py
│   ├── enhanced_browser_manager.py
│   ├── session_manager.py
│   └── selector_strategies.py
├── hybrid/
│   ├── __init__.py
│   ├── handler.py
│   └── fallback_manager.py
├── security/
│   ├── __init__.py
│   ├── api_key_manager.py
│   └── encryption.py
└── monitoring/
    ├── __init__.py
    ├── performance_tracker.py
    └── cost_analyzer.py
```

### 5.2 新しい依存関係
```txt
# 既存の依存関係に追加
openai==1.12.0
anthropic==0.18.0
google-generativeai==0.3.2
keyring==24.3.0
cryptography==42.0.0
aiofiles==23.2.1
prometheus-client==0.19.0
```

## 6. 期待される効果

### 6.1 パフォーマンス向上
- 処理速度: 50-70%向上（API利用時）
- 並列処理による効率化: 3-5倍のスループット
- エラー率: 40%から10%以下に削減

### 6.2 運用面の改善
- 手動ログイン不要（API利用時）
- 24時間365日の自動実行が可能
- メンテナンスコストの大幅削減

### 6.3 コスト効果
- 初期は若干のAPI利用料が発生
- 長期的には人的コストの削減で相殺
- スケールメリットによるコスト最適化

## 7. リスクと対策

### 7.1 技術的リスク
- **API制限**: レート制限への対応、適切なスロットリング
- **セキュリティ**: API keyの厳重な管理、定期的な更新
- **互換性**: 各AIサービスのAPI変更への対応

### 7.2 運用リスク
- **移行期間**: ハイブリッド実装による段階的移行
- **ユーザー教育**: 詳細なドキュメントとトレーニング
- **バックアップ**: ブラウザ自動化への即座のフォールバック

## 8. まとめ

この改善計画により、現在の手動プロセスと不安定な動作から、完全自動化された堅牢なシステムへの移行が可能になります。段階的なアプローチにより、リスクを最小限に抑えながら、着実に改善を進めることができます。