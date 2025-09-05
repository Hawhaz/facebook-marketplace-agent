# Facebook Marketplace Agent

Agente autónomo para automatizar publicaciones en Facebook Marketplace

## Descripción

Este proyecto es un agente inteligente que automatiza el proceso de publicación de propiedades en Facebook Marketplace, integrándose con scrapers de datos de Century21 y otros sitios inmobiliarios.

## Características

- 🤖 Automatización completa de publicaciones en Facebook Marketplace
- 🏠 Scraping de datos de propiedades desde Century21
- 📸 Descarga y procesamiento automático de imágenes
- 🔥 Integración con Firebase para almacenamiento de datos
- ☁️ Almacenamiento de imágenes en Google Cloud Storage
- 🚀 API REST con FastAPI
- 🐳 Containerización con Docker
- 📊 Monitoreo y métricas con Prometheus/Grafana

## Estructura del Proyecto

```
facebook-marketplace-agent/
├── app/
│   ├── api/                 # API endpoints
│   ├── core/               # Core business logic
│   │   └── automation/     # Automation modules
│   │       └── facebook/   # Facebook-specific automation
│   ├── db/                 # Database connections
│   ├── integrations/       # External integrations
│   ├── models/             # Data models
│   └── utils/              # Utility functions
├── scripts/                # Utility scripts
├── examples/               # Example data and images
├── docs/                   # Documentation
└── tests/                  # Test suite
```

## Instalación

1. Clona el repositorio:
```bash
git clone https://github.com/Hawhaz/facebook-marketplace-agent.git
cd facebook-marketplace-agent
```

2. Instala las dependencias:
```bash
pip install -r requirements.txt
```

3. Instala los navegadores de Playwright:
```bash
playwright install
```

4. Configura las variables de entorno:
```bash
cp .env.example .env
# Edita .env con tus credenciales
```

5. Ejecuta el setup:
```bash
python setup.py
```

## Uso

### Ejecutar la API
```bash
python -m app.main
```

### Ejecutar scripts de prueba
```bash
python -m scripts.test_professional_agent
```

### Con Docker
```bash
docker-compose up
```

## Configuración

El proyecto utiliza variables de entorno para la configuración. Consulta `.env.example` para ver todas las opciones disponibles.

### Variables principales:
- `SECRET_KEY`: Clave secreta para la aplicación
- `FIREBASE_PROJECT_ID`: ID del proyecto Firebase
- `FACEBOOK_EMAIL`: Email de Facebook (opcional)
- `FACEBOOK_PASSWORD`: Password de Facebook (opcional)

## Contribución

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para detalles.

## Soporte

Si tienes problemas o preguntas, por favor abre un issue en GitHub.
