import os
from   threading          import Thread

from   flask              import Flask
from   flask_cors         import CORS
from   flask_jwt_extended import JWTManager

from   config.orm         import db

from   tasks.startup      import resume_svcs
from   tasks.consumer     import kafka_consumer_routine

from   utils.kafka_admin_client import create_kafka_topics

# import modules
from   modules            import oauth_module, user_module, media_module, search_module


# init server
app = Flask(__name__)

# config server
app.url_map.strict_slashes       = False
app.json.sort_keys               = False
app.secret_key                   = os.environ["FLASK_SECRET_KEY"]

# config uploads
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 1024  # 1 GiB Max
app.config["UPLOAD_FOLDER"]      = os.environ["UPLOAD_FOLDER"]
temp_upload_path                 = os.path.join(app.config["UPLOAD_FOLDER"], "temp")
if not os.path.exists(temp_upload_path):
    os.mkdir(temp_upload_path)

# init CORS
CORS(app)

# config PyJWT (flask_jwt_extended)
app.config["JWT_SECRET_KEY"]           = os.environ["JWT_SECRET_KEY"]
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = False
app.config["JWT_ENCODE_NBF"]           = False
JWTManager(app)

# init db
app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql+psycopg://{os.environ["POSTGRES_USER"]}:{os.environ["POSTGRES_PASSWORD"]}@db:5432/{os.environ["POSTGRES_DB"]}"
db.init_app(app)
with app.app_context():
    db.create_all()


# init kafka
create_kafka_topics()  # create kafka topic(s)
Thread(daemon=True, target=kafka_consumer_routine, args=(app.app_context(),)).start()  # init kafka consumer worker


# run server resume routine
resume_svcs(app.app_context())


# register modules
module_blueprints = [
    oauth_module.blueprint,
    user_module.blueprint,
    media_module.blueprint,
    search_module.blueprint
]
for mbp in module_blueprints:
    app.register_blueprint(mbp)

