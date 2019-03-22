KindleGalleryPusher📷
==========

[demoはこちら](http://gallery.lpanda.net/)


貴方の写真集をみんなたシェアしませんか？

# 1. このサイトアの向いた人
* 自分の写真集をkindleでもみたい
* kindleを使っている友達にシェアしたい


# 2. このサイトについて
* アプロードした写真集を自動に*mobi* *epub* フォーマットに変換します
* 気に入った写真集を直接に貴方のkindleデバイスに送信できます

## 2.1. requirements
> * Django>2.1
> * awesome-slugify
> * mysqlclient
> * python-cv2
> * Pillow
> * psutil
> * requests
> * beautifulsoup4
> * lxml
> * [django suit-v2 ](https://django-suit.readthedocs.io/en/v2/)
> * django-clean 

## 2.2. thanks for 
> * [KCC](https://github.com/ciromattia/kcc)
 
 ## データベースに関して
 
1.  データベースは*mysql*を使います。*KindleGalleryPusher/settings.py*で、下の部分を編集してください。
    ```python
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'kindleGallerysite',
            'USER': 'your_mysql_username',
            'PASSWORD': 'your_mysql_password',
            'HOST': '127.0.0.1',
        }
    }
    ```
2. 次にmysqlでデータベースを作ります
    ```sql
    CREATE DATABASE kindleGallerysite
    ```


### 2.2.1. mysqlに関して

現在mysqlの最新バージョンは*8.0*です。*mysql 8.0*から、新しいパスワード暗号化方法が導入されました。

しかし、現在の*django*はこの新しい暗号化方式を支援していませんので、もし*mysql 8.0*以上のバージョンを使うなら、暗号化方式を*Legacy Authentication Method*に変更してください

### 2.2.2. sqlite に関して

もしsqliteを使いたいなら、*KindleGalleryPusher/settings.py* の*DATABASES*を下のように変更したください

``` python
    DATABASES = {
        'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'datas.sql',
        }
    }
```

## 2.3. 送信に関して

詳しいkindleの送信機能説明はアマゾンのページをご覧ください。

[Kindleパーソナル・ドキュメントサービス](https://www.amazon.co.jp/gp/help/customer/display.html/ref=kinw_myk_pd_ln?ie=UTF8&nodeId=200767340#assignemail)

簡単に言うと、Kindleの送信機能はつまり
> 送信したいファイルを添付ファイルとして、eメールの形でkindleデバイスと連携しているメールボックスに送信する。
> 
> 送信後、kindleデバイスは自動に添付ファイルをダウンロードする

送信機能を有効にするため、*KindleGalleryPusher/settings.py* のsmtpを設定してください
```python
EMAIL_HOST = 'smtp.yourserver.net'
EMAIL_HOST_USER = 'your email'
EMAIL_HOST_PASSWORD = 'your_smtp_password'
```

また、*pushmonitor/mailsender.py*　も同じく設定してください

```python
smtp_username = 'your email'
smtp_password = 'your_smtp_password'
smtp_hostname = 'smtp.yourserver.net'
```

## 2.4. hostnameに関して

*KindleGalleryPusher/settings.py*の*ALLOWED_HOSTS* 部分で、自分のdonamを入れてください

```python
ALLOWED_HOSTS = ['gallery.lpanda.net', 'localhost', '127.0.0.1']
```

## 2.5. ユーザデータ容量に関して

不正な大量ダウンロードでサーバを高負荷状態にさせることを防ぐため、データ容量制度を導入しました。（携帯のデータ容量と同じ感じ）

* アカウントのデフォルトデータ容量は *1GB* です
* 毎回ファイルをダウンロードする時、データ容量が削られます
* データ容量が0になったら、ダウンロードすることが不可能になります
* また、ユーザの全部のダウンロード履歴も記録されます
* 毎回データ容量は *1GB* に回復します

もし *1GB*　のデータ容量を調整したいなら、 *account/models.py* の *USER_BASE_BANDWIDTH*　を調整したください