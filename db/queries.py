from db.database import get_pool

# ── Районы ────────────────────────────────────────────────
async def get_districts():
    pool = await get_pool()
    return await pool.fetch("SELECT * FROM districts WHERE is_active=true ORDER BY sort_order")

async def get_district(dist_id: int):
    pool = await get_pool()
    return await pool.fetchrow("SELECT * FROM districts WHERE id=$1", dist_id)

# ── Категории ─────────────────────────────────────────────
async def get_categories():
    pool = await get_pool()
    return await pool.fetch("SELECT * FROM categories WHERE is_active=true ORDER BY sort_order")

async def get_category(cat_id: int):
    pool = await get_pool()
    return await pool.fetchrow("SELECT * FROM categories WHERE id=$1", cat_id)

# ── Провайдеры ────────────────────────────────────────────
async def get_provider_by_tg(tg_id: int):
    pool = await get_pool()
    return await pool.fetchrow("SELECT * FROM providers WHERE tg_id=$1", tg_id)

async def create_provider(tg_id, tg_username, name, phone, category_id, district_id, description, address):
    pool = await get_pool()
    return await pool.fetchrow("""
        INSERT INTO providers
            (tg_id, tg_username, name, phone, category_id, district_id, description, address)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
        ON CONFLICT (tg_id) DO UPDATE SET
            name=$3, phone=$4, category_id=$5, district_id=$6,
            description=$7, address=$8, is_approved=false
        RETURNING *
    """, tg_id, tg_username, name, phone, category_id, district_id, description, address)

async def search_providers(category_id: int, district_id: int):
    pool = await get_pool()
    return await pool.fetch("""
        SELECT p.*, c.name AS cat_name, c.emoji AS cat_emoji,
               d.name AS district_name
        FROM providers p
        JOIN categories c ON p.category_id = c.id
        JOIN districts d ON p.district_id = d.id
        WHERE p.category_id=$1
          AND p.district_id=$2
          AND p.is_active=true
          AND p.is_approved=true
        ORDER BY p.created_at DESC
    """, category_id, district_id)

async def get_all_providers_admin(approved: bool = False):
    pool = await get_pool()
    return await pool.fetch("""
        SELECT p.*, c.name AS cat_name, d.name AS district_name
        FROM providers p
        JOIN categories c ON p.category_id = c.id
        JOIN districts d ON p.district_id = d.id
        WHERE p.is_approved=$1
        ORDER BY p.created_at DESC
    """, approved)

async def approve_provider(provider_id: int):
    pool = await get_pool()
    await pool.execute("UPDATE providers SET is_approved=true WHERE id=$1", provider_id)

async def reject_provider(provider_id: int):
    pool = await get_pool()
    await pool.execute("UPDATE providers SET is_active=false WHERE id=$1", provider_id)

# ── Клиенты ───────────────────────────────────────────────
async def get_or_create_client(tg_id, tg_username, name):
    pool = await get_pool()
    return await pool.fetchrow("""
        INSERT INTO clients (tg_id, tg_username, name)
        VALUES ($1,$2,$3)
        ON CONFLICT (tg_id) DO UPDATE SET tg_username=$2, name=$3
        RETURNING *
    """, tg_id, tg_username, name)

# ── Статистика ─────────────────────────────────────────────
async def log_search(client_id, category_id, district_id, results_count):
    pool = await get_pool()
    await pool.execute("""
        INSERT INTO searches (client_id, category_id, district_id, results_count)
        VALUES ($1,$2,$3,$4)
    """, client_id, category_id, district_id, results_count)

async def get_stats():
    pool = await get_pool()
    providers = await pool.fetchval("SELECT COUNT(*) FROM providers WHERE is_approved=true")
    pending   = await pool.fetchval("SELECT COUNT(*) FROM providers WHERE is_approved=false AND is_active=true")
    clients   = await pool.fetchval("SELECT COUNT(*) FROM clients")
    searches  = await pool.fetchval("SELECT COUNT(*) FROM searches")

    # По районам
    by_district = await pool.fetch("""
        SELECT d.name, COUNT(p.id) AS cnt
        FROM districts d
        LEFT JOIN providers p ON p.district_id=d.id AND p.is_approved=true
        GROUP BY d.id, d.name ORDER BY d.sort_order
    """)
    return providers, pending, clients, searches, by_district
