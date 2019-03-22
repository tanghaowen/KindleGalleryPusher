KindleGalleryPusher📷
==========

[demoはこちら](http://gallery.lpanda.net/)


貴方の写真集をみんなたシェアしませんか？

## このサイトアの向いた人
* 自分の写真集をkindleでもみたい
* kindleを使っている友達にシェアしたい


## このサイトについて
* アプロードした写真集を自動に*mobi* *epub* フォーマットに変換します
* 気に入った写真集を直接に貴方のkindleデバイスにプシュッできます

## requirements
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


### mysqlに関して

現在mysqlの最新バージョンは*8.0*です。*mysql 8.0*から、新しいパスワード暗号化方法が導入されました。

しかし、現在の*django*はこの新しい暗号化方式を支援していませんので、もし*mysql 8.0*以上のバージョンを使うなら、暗号化方式を*Legacy Authentication Method*に変更してください

### sqlite に関して

もしsqliteを使いたいなら、*KindleGalleryPusher/settings.py* の*DATABASES*を下のように変更したください

``` python
    DATABASES = {
        'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'datas.sql',
        }
    }
```

## プシュッに関して

詳しいkindleのプシュッ機能説明はアマゾンのページをご覧ください。

[Kindleパーソナル・ドキュメントサービス](https://www.amazon.co.jp/gp/help/customer/display.html/ref=kinw_myk_pd_ln?ie=UTF8&nodeId=200767340#assignemail)

簡単に言うと、Kindleのプシュッ機能はつまり
> 送信したいファイルを添付ファイルとして、eメールの形でkindleデバイスと連携しているメールボックスに送信する。
> 
> 送信後、kindleデバイスは自動に添付ファイルをダウンロードする

プシュッ機能を有効にするため、*KindleGalleryPusher/settings.py* のsmtpを設定してください
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


## hostnameに関して

*KindleGalleryPusher/settings.py*の*ALLOWED_HOSTS* 部分で、自分のdonamを入れてください

```python
ALLOWED_HOSTS = ['gallery.lpanda.net', 'localhost', '127.0.0.1']
```