# AWSアカウント取得・設定手順

`infra/lambda/`のデプロイ（`sam deploy`）を実行できるようにするための、AWSアカウント作成から
CLIセットアップまでの手順。すべてユーザー側の作業（ブラウザでのサインアップ、支払い情報の登録、
ローカルPCへのソフトウェアインストール）が必要で、Claude側では代行できない。

⚠️ **AWSのアクセスキー（Access Key ID / Secret Access Key）は絶対にチャットに貼り付けないこと。**
Googleサービスアカウントの鍵と違い、この作業ではClaude側でAWSを直接操作する手段がないため、
共有する必要も理由もない。設定できたかどうかは、自分のPC上でコマンドを実行して確認する。

---

## 1. AWSアカウントの作成

1. https://aws.amazon.com/jp/ にアクセスし、「無料アカウントを作成」
2. メールアドレス・アカウント名を入力
3. 連絡先情報を入力（個人 or 組織）
4. **支払い情報（クレジットカード）を登録** — Lambda/API Gatewayには無料利用枠があるが、
   登録自体には必須。今回の用途（月数回の議事録生成）であれば無料枠内に収まる見込み
5. 電話番号によるSMS/音声認証
6. サポートプランは「Basic（無料）」を選択

作成直後にログインするアカウントは「ルートユーザー」。日常的な操作には使わず、
次の手順で作業用のIAMユーザーを作る。

## 2. 予算アラートの設定（推奨）

意図しない課金に早く気づけるよう設定しておく。

1. https://console.aws.amazon.com/billing/home#/budgets を開く
2. 「予算を作成」→「ゼロベースの予算」または「テンプレート」→「月次コスト予算」
3. しきい値（例: 月5ドル）を決めて、通知先メールアドレスを設定

## 3. IAMユーザーの作成（デプロイ作業用）

1. https://console.aws.amazon.com/iam/home#/users にアクセス
2. 「ユーザーを作成」
   - ユーザー名: 例 `kitayama-minutes-deploy`
   - 「AWS マネジメントコンソールへのユーザーアクセスを提供する」は**チェックしない**
     （CLIでの利用のみのため）
3. 権限の設定 → 「ポリシーを直接アタッチする」
   - `AdministratorAccess` を選択する（一番簡単。個人の検証用アカウントであれば問題ない。
     組織のAWSアカウントを使う場合は、後述の「必要な権限」を参考に、IAM管理者に絞った
     権限を依頼すること）
4. 作成完了

### アクセスキーの発行

1. 作成した`kitayama-minutes-deploy`ユーザーの詳細画面を開く
2. 「セキュリティ認証情報」タブ →「アクセスキーを作成」
3. ユースケースは「コマンドラインインターフェイス (CLI)」を選択、確認事項にチェックして次へ
4. 表示された **アクセスキーID** と **シークレットアクセスキー** を控える
   （シークレットアクセスキーはこの画面でしか表示されない。忘れずにコピーすること）

### （参考）必要な権限を絞る場合

`AdministratorAccess`の代わりに、最低限このデプロイに必要な権限だけを付与する場合は、
以下のAWS管理ポリシーの組み合わせが目安（正確な絞り込みは運用しながら調整する）:
`AWSCloudFormationFullAccess`, `AWSLambda_FullAccess`, `AmazonAPIGatewayAdministrator`,
`AmazonEC2ContainerRegistryFullAccess`, `IAMFullAccess`（SAMがLambda実行ロールを
作成するため）。組織のセキュリティポリシーに応じて相談すること。

## 4. AWS CLIのインストール（自分のPC上で）

- macOS: `brew install awscli` または https://awscli.amazonaws.com/AWSCLIV2.pkg
- Windows: https://awscli.amazonaws.com/AWSCLIV2.msi
- Linux: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html

インストール確認:
```bash
aws --version
```

## 5. 認証情報の設定

```bash
aws configure
```

聞かれる項目:
- `AWS Access Key ID`: 手順3で控えたアクセスキーID
- `AWS Secret Access Key`: 手順3で控えたシークレットアクセスキー
- `Default region name`: `ap-northeast-1`（東京リージョン。日本国内からの利用ならこれが自然）
- `Default output format`: `json`（そのままEnterでも可）

### 確認

```bash
aws sts get-caller-identity
```

以下のようなJSONが返れば成功（`Arn`に手順3で作ったユーザー名が含まれていることを確認）:
```json
{
    "UserId": "...",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/kitayama-minutes-deploy"
}
```

## 6. Docker Desktopのインストール

`sam build`がコンテナイメージをビルドするために必要。

- https://www.docker.com/products/docker-desktop/ からOSに合わせてダウンロード・インストール
- インストール後、Docker Desktopを起動しておく（バックグラウンドで常駐していればOK）
- 確認: `docker --version` および `docker ps`（エラーが出なければ起動できている）

## 7. AWS SAM CLIのインストール

- macOS: `brew install aws-sam-cli`
- Windows/Linux: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html
- 確認: `sam --version`

---

ここまで終わったら、`infra/lambda/README.md`の「デプロイ手順」（`sam build` → `sam deploy --guided`）
に進める。
