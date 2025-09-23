"""メインアプリケーションファイル"""
from flask import Flask, render_template
from config import Config
from routes import api

def create_app():
    """Flaskアプリケーションのファクトリー関数"""
    app = Flask(__name__, static_folder='static', template_folder='templates')
    
    # 設定の検証
    Config.validate_config()
    
    # ブループリントを登録（/api配下にマウント）
    app.register_blueprint(api, url_prefix='/api')

    # フロントエンド: ルートページ
    @app.route('/home')
    @app.route('/')
    def index():
        return render_template('index.html')
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=Config.PORT, debug=Config.DEBUG)
