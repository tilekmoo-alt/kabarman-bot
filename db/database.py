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

        # Создаём таблицы если нет
        await conn.execute("""
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
            ALTER TABLE categories ADD COLUMN IF NOT EXISTS redirect_bot_url TEXT DEFAULT NULL;
        """)

        # Миграция: добавляем UNIQUE constraints через DO блок
        await conn.execute("""
            DO $$
            DECLARE
                min_id INTEGER;
            BEGIN
                -- ── districts ──────────────────────────────────────
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'districts_name_key'
                ) THEN
                    -- Для каждого дубля: переключаем ссылки из searches на min_id
                    FOR min_id IN
                        SELECT MIN(id) FROM districts GROUP BY name HAVING COUNT(*) > 1
                    LOOP
                        -- Обнуляем district_id в searches для дублирующихся записей
                        UPDATE searches
                        SET district_id = min_id
                        WHERE district_id IN (
                            SELECT id FROM districts
                            WHERE name = (SELECT name FROM districts WHERE id = min_id)
                            AND id != min_id
                        );

                        -- Удаляем дубли
                        DELETE FROM districts
                        WHERE name = (SELECT name FROM districts WHERE id = min_id)
                        AND id != min_id;
                    END LOOP;

                    ALTER TABLE districts ADD CONSTRAINT districts_name_key UNIQUE (name);
                END IF;

                -- ── categories ─────────────────────────────────────
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'categories_name_key'
                ) THEN
                    UPDATE searches s
                    SET category_id = (
                        SELECT MIN(id) FROM categories c WHERE c.name = (
                            SELECT name FROM categories WHERE id = s.category_id
                        )
                    )
                    WHERE category_id IN (
                        SELECT id FROM categories
                        WHERE name IN (
                            SELECT name FROM categories GROUP BY name HAVING COUNT(*) > 1
                        )
                        AND id NOT IN (SELECT MIN(id) FROM categories GROUP BY name)
                    );

                    UPDATE providers p
                    SET category_id = (
                        SELECT MIN(id) FROM categories c WHERE c.name = (
                            SELECT name FROM categories WHERE id = p.category_id
                        )
                    )
                    WHERE category_id IN (
                        SELECT id FROM categories
                        WHERE name IN (
                            SELECT name FROM categories GROUP BY name HAVING COUNT(*) > 1
                        )
                        AND id NOT IN (SELECT MIN(id) FROM categories GROUP BY name)
                    );

                    DELETE FROM categories
                    WHERE id NOT IN (SELECT MIN(id) FROM categories GROUP BY name);

                    ALTER TABLE categories ADD CONSTRAINT categories_name_key UNIQUE (name);
                END IF;
            END $$;
        """)

        # Вставляем/обновляем районы
        await conn.execute("""
            INSERT INTO districts (name, name_ky, sort_order) VALUES
                ('Каракол',    'Каракол',     1),
                ('Ак-Суу',     'Ак-Суу',      2),
                ('Тюп',        'Тюп',         3),
                ('Жети-Огуз',  'Жети-Өгүз',   4),
                ('Тон',        'Тон',         5),
                ('Чолпон-Ата', 'Чолпон-Ата',  6)
            ON CONFLICT (name) DO UPDATE SET sort_order = EXCLUDED.sort_order;
        """)

        # Вставляем/обновляем категории
        realty_bot = os.getenv("REALTY_BOT_URL", "https://t.me/kabarman_realty_bot")
        await conn.execute("""
            INSERT INTO categories (name, emoji, sort_order, redirect_bot_url) VALUES
                ('Кафе и рестораны',  '🍽️',  1,  NULL),
                ('Доставка еды',       '🛵',   2,  NULL),
                ('Красота и здоровье', '💅',   3,  NULL),
                ('Ремонт и стройка',   '🔨',   4,  NULL),
                ('Сантехника',         '🔧',   5,  NULL),
                ('Электрика',          '⚡',   6,  NULL),
                ('Репетиторы',         '📚',   7,  NULL),
                ('Грузоперевозки',     '🚛',   8,  NULL),
                ('Недвижимость',       '🏠',   9,  $1),
                ('Фото и видео',       '📸',  10,  NULL),
                ('IT и компьютеры',    '💻',  11,  NULL),
                ('Другие услуги',      '📋',  12,  NULL)
            ON CONFLICT (name) DO UPDATE SET
                emoji = EXCLUDED.emoji,
                sort_order = EXCLUDED.sort_order;
        """, realty_bot)

    print("✅ База данных Кабарман готова")
