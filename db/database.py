import asyncpg
import os

_pool = None

async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(os.getenv("DATABASE_URL"), min_size=2, max_size=10)
    return _pool

async def setup_db():
    pool = await get_pool()
    async with pool.acquire() as conn:

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS oblasts (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                sort_order INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT true
            );

            CREATE TABLE IF NOT EXISTS districts (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                name_ky TEXT,
                sort_order INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT true
            );

            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                emoji TEXT DEFAULT '📋',
                sort_order INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT true,
                redirect_bot_url TEXT DEFAULT NULL
            );

            CREATE TABLE IF NOT EXISTS providers (
                id SERIAL PRIMARY KEY,
                tg_id BIGINT NOT NULL,
                tg_username TEXT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                category_id INTEGER REFERENCES categories(id),
                district_id INTEGER REFERENCES districts(id),
                description TEXT,
                address TEXT,
                social_link TEXT,
                is_active BOOLEAN DEFAULT true,
                is_approved BOOLEAN DEFAULT false,
                created_at TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS clients (
                id SERIAL PRIMARY KEY,
                tg_id BIGINT UNIQUE NOT NULL,
                tg_username TEXT,
                name TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS searches (
                id SERIAL PRIMARY KEY,
                client_id INTEGER REFERENCES clients(id),
                category_id INTEGER REFERENCES categories(id),
                district_id INTEGER REFERENCES districts(id),
                query TEXT,
                results_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        # Добавляем колонки если нет
        await conn.execute("""
            ALTER TABLE providers ADD COLUMN IF NOT EXISTS social_link TEXT;
            ALTER TABLE searches ADD COLUMN IF NOT EXISTS query TEXT;
            ALTER TABLE searches ADD COLUMN IF NOT EXISTS district_id INTEGER REFERENCES districts(id);
            ALTER TABLE categories ADD COLUMN IF NOT EXISTS redirect_bot_url TEXT DEFAULT NULL;
            ALTER TABLE districts ADD COLUMN IF NOT EXISTS oblast_id INTEGER REFERENCES oblasts(id);
        """)

        # Миграция: удаляем UNIQUE(tg_id) с providers
        await conn.execute("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'providers_tg_id_key'
                ) THEN
                    ALTER TABLE providers DROP CONSTRAINT providers_tg_id_key;
                END IF;
            END $$;
        """)

        # Миграция: добавляем UNIQUE на districts.name и categories.name
        await conn.execute("""
            DO $$
            DECLARE
                min_id INTEGER;
                dist_name TEXT;
                cat_name TEXT;
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'districts_name_key'
                ) THEN
                    FOR min_id, dist_name IN
                        SELECT MIN(id), name FROM districts GROUP BY name HAVING COUNT(*) > 1
                    LOOP
                        UPDATE searches SET district_id = min_id
                        WHERE district_id IN (
                            SELECT id FROM districts WHERE name = dist_name AND id != min_id
                        );
                        DELETE FROM districts WHERE name = dist_name AND id != min_id;
                    END LOOP;
                    ALTER TABLE districts ADD CONSTRAINT districts_name_key UNIQUE (name);
                END IF;

                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'categories_name_key'
                ) THEN
                    FOR min_id, cat_name IN
                        SELECT MIN(id), name FROM categories GROUP BY name HAVING COUNT(*) > 1
                    LOOP
                        UPDATE searches SET category_id = min_id
                        WHERE category_id IN (
                            SELECT id FROM categories WHERE name = cat_name AND id != min_id
                        );
                        UPDATE providers SET category_id = min_id
                        WHERE category_id IN (
                            SELECT id FROM categories WHERE name = cat_name AND id != min_id
                        );
                        DELETE FROM categories WHERE name = cat_name AND id != min_id;
                    END LOOP;
                    ALTER TABLE categories ADD CONSTRAINT categories_name_key UNIQUE (name);
                END IF;
            END $$;
        """)

        # Вставляем области
        await conn.execute("""
            INSERT INTO oblasts (name, sort_order) VALUES
                ('Бишкек',               1),
                ('Ош',                   2),
                ('Чуйская область',      3),
                ('Иссык-Кульская обл.',  4),
                ('Жалал-Абадская обл.',  5),
                ('Ошская область',       6),
                ('Нарынская область',    7),
                ('Таласская область',    8),
                ('Баткенская область',   9)
            ON CONFLICT (name) DO NOTHING;
        """)

        # Привязываем существующие районы Иссык-Куля к области
        await conn.execute("""
            UPDATE districts
            SET oblast_id = (SELECT id FROM oblasts WHERE name = 'Иссык-Кульская обл.')
            WHERE name IN ('Каракол','Ак-Суу','Тюп','Жети-Огуз','Тон','Чолпон-Ата')
              AND oblast_id IS NULL;
        """)

        # Обновляем/вставляем все районы с привязкой к области
        await conn.execute("""
            INSERT INTO districts (name, sort_order, oblast_id)
            SELECT v.dname, v.sorder, o.id
            FROM (VALUES
                ('Каракол',       1::int, 'Иссык-Кульская обл.'),
                ('Чолпон-Ата',    2::int, 'Иссык-Кульская обл.'),
                ('Ак-Суу',        3::int, 'Иссык-Кульская обл.'),
                ('Тюп',           4::int, 'Иссык-Кульская обл.'),
                ('Жети-Огуз',     5::int, 'Иссык-Кульская обл.'),
                ('Тон',           6::int, 'Иссык-Кульская обл.'),
                ('Бишкек',        1::int, 'Бишкек'),
                ('Ош',            1::int, 'Ош'),
                ('Кара-Балта',    1::int, 'Чуйская область'),
                ('Кант',          2::int, 'Чуйская область'),
                ('Токмок',        3::int, 'Чуйская область'),
                ('Сокулук',       4::int, 'Чуйская область'),
                ('Аламудун',      5::int, 'Чуйская область'),
                ('Кемин',         6::int, 'Чуйская область'),
                ('Жалал-Абад',    1::int, 'Жалал-Абадская обл.'),
                ('Таш-Кумыр',     2::int, 'Жалал-Абадская обл.'),
                ('Кара-Куль',     3::int, 'Жалал-Абадская обл.'),
                ('Базар-Коргон',  4::int, 'Жалал-Абадская обл.'),
                ('Кара-Суу',      1::int, 'Ошская область'),
                ('Узген',         2::int, 'Ошская область'),
                ('Ноокат',        3::int, 'Ошская область'),
                ('Нарын',         1::int, 'Нарынская область'),
                ('Ат-Баши',       2::int, 'Нарынская область'),
                ('Кочкор',        3::int, 'Нарынская область'),
                ('Талас',         1::int, 'Таласская область'),
                ('Бакай-Ата',     2::int, 'Таласская область'),
                ('Баткен',        1::int, 'Баткенская область'),
                ('Кадамжай',      2::int, 'Баткенская область'),
                ('Лейлек',        3::int, 'Баткенская область')
            ) AS v(dname, sorder, oname)
            JOIN oblasts o ON o.name = v.oname
            ON CONFLICT (name) DO UPDATE SET oblast_id = EXCLUDED.oblast_id;
        """)

        # Вставляем категории
        realty_bot = os.getenv("REALTY_BOT_URL", "https://t.me/kabarman_realty_bot")
        await conn.execute("""
            INSERT INTO categories (name, emoji, sort_order, redirect_bot_url) VALUES
                ('Кафе и рестораны',  '🍽️',  1,  NULL),
                ('Доставка еды',       '🛵',   2,  NULL),
                ('Красота и здоровье', '💅',   3,  NULL),
                ('Ремонт и стройка',   '🔨',   4,  NULL),
                ('Сантехника',         '🔧',   5,  NULL),
                ('Электрика',          '⚡',   6,  NULL),
                ('Ателье и пошив',     '🧵',   7,  NULL),
                ('Автосервис (СТО)',   '🚗',   8,  NULL),
                ('Прокат',             '🎿',   9,  NULL),
                ('Репетиторы',         '📚',  10,  NULL),
                ('Грузоперевозки',     '🚛',  11,  NULL),
                ('Недвижимость',       '🏠',  12,  $1),
                ('Фото и видео',       '📸',  13,  NULL),
                ('IT и компьютеры',    '💻',  14,  NULL),
                ('Производство',       '🏭',  15,  NULL),
                ('Другие услуги',      '📋',  16,  NULL)
            ON CONFLICT (name) DO UPDATE SET
                emoji = EXCLUDED.emoji,
                sort_order = EXCLUDED.sort_order;
        """, realty_bot)

        # Таблица объявлений (marketplace)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS listings (
                id            SERIAL PRIMARY KEY,
                title         TEXT NOT NULL,
                description   TEXT,
                price         INTEGER,
                is_negotiable BOOLEAN DEFAULT false,
                photos        TEXT[] DEFAULT '{}',
                category      TEXT NOT NULL,
                oblast_id     INTEGER REFERENCES oblasts(id),
                district_id   INTEGER REFERENCES districts(id),
                contact_name  TEXT,
                contact_phone TEXT NOT NULL,
                tg_username   TEXT,
                tg_id         BIGINT,
                source        TEXT DEFAULT 'web',
                is_active     BOOLEAN DEFAULT true,
                expires_at    TIMESTAMP DEFAULT NOW() + INTERVAL '30 days',
                created_at    TIMESTAMP DEFAULT NOW()
            );
        """)

    print("✅ База данных Кабарман готова")
