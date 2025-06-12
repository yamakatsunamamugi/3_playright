# 担当者A（競合解決・マージ担当）作業指示書

## 1. 担当範囲
- Gitブランチのマージ作業全般
- マージ時の競合解決
- 統合ブランチの管理
- 各機能の基本動作確認

## 2. 前提条件
- 現在のブランチ: feature/integration
- マージ対象ブランチ:
  - feature/gui-enhancement（競合発生中）
  - feature/sheets-processing
  - feature/ai-automation

## 3. 作業手順

### 3.1 現在の競合解決（最優先）
```bash
# 1. 現在の状況確認
git status

# 2. 競合ファイルの解決
# test_gui.pyの競合を解決
# 統合版として両方の機能を活かす形で修正

# 3. 解決済みファイルの追加
git add src/config_manager.py
git add test_gui.py

# 4. マージコミット
git commit -m "merge: feature/gui-enhancement を統合、競合を解決"
```

### 3.2 残りのブランチマージ
```bash
# 1. sheets-processingブランチのマージ
git merge feature/sheets-processing
# 競合が発生した場合は、以下の方針で解決：
# - インターフェースは統一版を採用
# - 機能は両方を残す
# - 設定ファイルは統合版に集約

# 2. ai-automationブランチのマージ
git merge feature/ai-automation
# 同様の方針で競合解決
```

### 3.3 競合解決の方針
1. **config_manager.py**: 全機能を含む統合版を採用
2. **インターフェース系ファイル**: src/interfaces/配下の統一版を採用
3. **テストファイル**: 両方のテストを残し、重複は削除
4. **その他**: 機能を損なわない形で統合

## 4. Git管理詳細

### 4.1 ブランチ戦略
```
main
 └── feature/integration（現在地）
      ├── マージ: feature/gui-enhancement
      ├── マージ: feature/sheets-processing
      └── マージ: feature/ai-automation
```

### 4.2 コミットメッセージ規則
```
merge: [ブランチ名] を統合、[対応内容]
fix: マージ競合を解決 - [ファイル名]
refactor: 統合に伴う調整 - [内容]
```

### 4.3 プッシュタイミング
- 各ブランチのマージ完了後
- 大きな競合解決の完了後
- 他のメンバーとの同期が必要な時

## 5. 連携事項

### 5.1 B担当者への引き継ぎ
- マージ完了後、すぐに通知
- 競合で変更した箇所のリストを共有
- 特に注意が必要な統合部分を明記

### 5.2 C担当者への情報共有
- テストが必要な統合部分のリスト
- 動作確認で見つけた問題点

### 5.3 統括者Dへの報告
- 各マージの完了状況
- 発生した競合と解決方法
- 残課題のリスト

## 6. エラー時の対処

### 6.1 マージ中止
```bash
git merge --abort  # マージを中止して元の状態に戻る
```

### 6.2 競合が複雑な場合
1. 一旦マージを中止
2. 該当ファイルの両バージョンを別名で保存
3. 統括者Dと相談の上、解決方針を決定

## 7. 完了条件
- [ ] feature/gui-enhancementのマージ完了
- [ ] feature/sheets-processingのマージ完了  
- [ ] feature/ai-automationのマージ完了
- [ ] 全ての競合解決
- [ ] 基本動作確認（アプリ起動、各画面遷移）
- [ ] git logで統合履歴の確認

## 8. 注意事項
- 競合解決時は機能を損なわないことを最優先
- 不明な点は即座に統括者Dに確認
- コミット前に必ずdiffを確認
- 大きな変更は他メンバーに事前通知