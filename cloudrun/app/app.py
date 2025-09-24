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

    # グローバル例外ハンドラ（未捕捉例外でも200でJSONを返す）
    @app.errorhandler(Exception)
    def handle_unhandled_error(e):
        import traceback
        from flask import jsonify
        return jsonify({
            "status": "error",
            "message": "unhandled_exception",
            "fallback_used": True,
            "debug_error": f"{str(e)} | traceback={traceback.format_exc(limit=5)}"
        })

    # フロントエンド: ルートページ
    @app.route('/home')
    @app.route('/')
    def index():
        return render_template('index.html')
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=Config.PORT, debug=Config.DEBUG)
