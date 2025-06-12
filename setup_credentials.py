#!/usr/bin/env python3
"""
Google Sheets API認証設定ヘルパー
"""

import os
import json
from pathlib import Path

def setup_credentials():
    """認証情報セットアップのガイド"""
    
    credentials_dir = Path("credentials")
    credentials_file = credentials_dir / "google_service_account.json"
    
    print("📋 Google Sheets API 認証設定")
    print("=" * 50)
    
    # ディレクトリ作成
    credentials_dir.mkdir(exist_ok=True)
    print(f"✅ 認証情報ディレクトリ作成: {credentials_dir}")
    
    if credentials_file.exists():
        print(f"✅ 認証ファイルが見つかりました: {credentials_file}")
        
        # ファイル内容確認
        try:
            with open(credentials_file, 'r') as f:
                creds = json.load(f)
            
            print("📄 認証情報:")
            print(f"   • プロジェクトID: {creds.get('project_id', 'N/A')}")
            print(f"   • クライアントメール: {creds.get('client_email', 'N/A')}")
            print(f"   • タイプ: {creds.get('type', 'N/A')}")
            
            return True, creds.get('client_email')
            
        except json.JSONDecodeError:
            print("❌ 認証ファイルの形式が正しくありません")
            return False, None
    else:
        print("❌ 認証ファイルが見つかりません")
        print()
        print("📥 次の手順で認証ファイルを配置してください:")
        print("1. Google Cloud Console からダウンロードしたJSONファイルを")
        print(f"2. 以下の場所にコピー: {credentials_file}")
        print("3. ファイル名を 'google_service_account.json' に変更")
        print()
        print("💡 ヒント:")
        print("   ダウンロードしたファイル名は通常:")
        print("   'project-name-123456-abcdef123456.json' の形式です")
        
        return False, None

def test_credentials():
    """認証情報をテスト"""
    try:
        from google.auth import load_credentials_from_file
        from googleapiclient.discovery import build
        
        credentials_file = "credentials/google_service_account.json"
        
        # 認証情報読み込み
        credentials, project = load_credentials_from_file(
            credentials_file,
            scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
        )
        
        # Google Sheets API クライアント作成
        service = build('sheets', 'v4', credentials=credentials)
        
        print("✅ Google Sheets API 認証成功!")
        return True, service
        
    except FileNotFoundError:
        print("❌ 認証ファイルが見つかりません")
        return False, None
    except Exception as e:
        print(f"❌ 認証エラー: {e}")
        return False, None

if __name__ == "__main__":
    # 認証設定確認
    success, client_email = setup_credentials()
    
    if success:
        print("\n🧪 認証テスト実行中...")
        test_success, service = test_credentials()
        
        if test_success:
            print("\n🎉 セットアップ完了!")
            print(f"📧 このメールアドレスをスプレッドシートに共有してください:")
            print(f"   {client_email}")
        else:
            print("\n❌ 認証テスト失敗")
    else:
        print("\n⚠️  認証ファイルを配置してから再実行してください")
        print("   python3 setup_credentials.py")