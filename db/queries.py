from db.database import get_pool

# ── Области ───────────────────────────────────────────────
async def get_oblasts():
    pool = await get_pool()
    return await pool.fetch("SELECT * FROM oblasts WHERE is_active=true ORDER BY sort_order")

async def get_oblast(oblast_id: int):
    pool = await get_pool()
    return await pool.fetchrow("SELECT * FROM oblasts WHERE id=$1", oblast_id)

# ── Районы ────────────────────────────────────────────────
async def get_districts():
    pool = await get_pool()
    return await pool.fetch("SELECT * FROM districts WHERE is_active=true ORDER BY sort_order")

async def get_districts_by_oblast(oblast_id: int):
    pool = await get_pool()
    return await pool.fetch(
        "SELECT * FROM districts WHERE oblast_id=$1 AND is_active=true ORDER BY sort_order",
        oblast_id
    )

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
async def get_providers_by_tg(tg_id: int):
    pool = await get_pool()
    return await pool.fetch("""
        SELECT p.*, c.name AS cat_name, c.emoji AS cat_emoji,
               d.name AS district_name
        FROM providers p
        JOIN categories c ON p.category_id = c.id
        JOIN districts d ON p.district_id = d.id
        WHERE p.tg_id=$1 AND p.is_active=true
        ORDER BY p.created_at DESC
    """, tg_id)

async def get_provider_by_id(provider_id: int):
    pool = await get_pool()
    return await pool.fetchrow("SELECT * FROM providers WHERE id=$1", provider_id)

async def create_provider(tg_id, tg_username, name, phone, category_id,
                           district_id, description, address, social_link=None):
    pool = await get_pool()
    return await pool.fetchrow("""
        INSERT INTO providers
            (tg_id, tg_username, name, phone, category_id,
             district_id, description, address, social_link)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
        RETURNING *
    """, tg_id, tg_username, name, phone, category_id,
         district_id, description, address, social_link)

async def delete_provider(provider_id: int, tg_id: int):
    pool = await get_pool()
    return await pool.execute("""
        UPDATE providers SET is_active=false
        WHERE id=$1 AND tg_id=$2
    """, provider_id, tg_id)

async def admin_delete_provider(provider_id: int):
    pool = await get_pool()
    await pool.execute("UPDATE providers SET is_active=false WHERE id=$1", provider_id)

async def search_providers(category_id: int, district_id: int):
    pool = await get_pool()
    return await pool.fetch("""
        SELECT p.*, c.name AS cat_name, c.emoji AS cat_emoji,
               d.name AS district_name
        FROM providers p
        JOIN categories c ON p.category_id = c.id
        JOIN districts d ON p.district_id = d.id
        WHERE p.category_id=$1 AND p.district_id=$2
          AND p.is_active=true AND p.is_approved=true
        ORDER BY p.created_at DESC
    """, category_id, district_id)

async def search_providers_by_text(query: str):
    pool = await get_pool()
    q = f"%{query.lower()}%"
    return await pool.fetch("""
        SELECT p.*, c.name AS cat_name, c.emoji AS cat_emoji,
               d.name AS district_name
        FROM providers p
        JOIN categories c ON p.category_id = c.id
        JOIN districts d ON p.district_id = d.id
        WHERE p.is_active=true AND p.is_approved=true
          AND (LOWER(p.name) LIKE $1
            OR LOWER(p.description) LIKE $1
            OR LOWER(c.name) LIKE $1
            OR LOWER(d.name) LIKE $1)
        ORDER BY p.created_at DESC
        LIMIT 10
    """, q)

async def get_all_providers_admin(approved: bool = False):
    pool = await get_pool()
    return await pool.fetch("""
        SELECT p.*, c.name AS cat_name, d.name AS district_name
        FROM providers p
        JOIN categories c ON p.category_id = c.id
        JOIN districts d ON p.district_id = d.id
        WHERE p.is_approved=$1 AND p.is_active=true
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

# ── Объявления ────────────────────────────────────────────
async def create_listing(title, description, price, is_negotiable,
                          photos, category, oblast_id, district_id,
                          contact_name, contact_phone, tg_username, tg_id, source='bot'):
    pool = await get_pool()
    return await pool.fetchrow("""
        INSERT INTO listings (title, description, price, is_negotiable,
            photos, category, oblast_id, district_id,
            contact_name, contact_phone, tg_username, tg_id, source)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
        RETURNING *
    """, title, description, price, is_negotiable,
        photos, category, oblast_id, district_id,
        contact_name, contact_phone, tg_username, tg_id, source)

async def get_listings(category=None, oblast_id=None, district_id=None, limit=20, offset=0):
    pool = await get_pool()
    conditions = ["is_active=true", "expires_at > NOW()"]
    params = []
    if category:
        params.append(category)
        conditions.append(f"category=${len(params)}")
    if oblast_id:
        params.append(oblast_id)
        conditions.append(f"oblast_id=${len(params)}")
    if district_id:
        params.append(district_id)
        conditions.append(f"district_id=${len(params)}")
    params += [limit, offset]
    where = " AND ".join(conditions)
    return await pool.fetch(f"""
        SELECT l.*, o.name AS oblast_name, d.name AS district_name
        FROM listings l
        LEFT JOIN oblasts o ON l.oblast_id = o.id
        LEFT JOIN districts d ON l.district_id = d.id
        WHERE {where}
        ORDER BY l.created_at DESC
        LIMIT ${len(params)-1} OFFSET ${len(params)}
    """, *params)

async def get_listings_by_tg(tg_id: int):
    pool = await get_pool()
    return await pool.fetch("""
        SELECT * FROM listings WHERE tg_id=$1 AND is_active=true ORDER BY created_at DESC
    """, tg_id)

async def deactivate_listing(listing_id: int, tg_id: int = None):
    pool = await get_pool()
    if tg_id is not None:
        await pool.execute(
            "UPDATE listings SET is_active=false WHERE id=$1 AND tg_id=$2",
            listing_id, tg_id
        )
    else:
        await pool.execute(
            "UPDATE listings SET is_active=false WHERE id=$1",
            listing_id
        )

# ── Статистика ────────────────────────────────────────────
async def log_search(client_id, category_id, district_id, results_count, query=None):
    pool = await get_pool()
    await pool.execute("""
        INSERT INTO searches (client_id, category_id, district_id, results_count, query)
        VALUES ($1,$2,$3,$4,$5)
    """, client_id, category_id, district_id, results_count, query)

async def get_stats():
    pool = await get_pool()
    providers   = await pool.fetchval("SELECT COUNT(*) FROM providers WHERE is_approved=true AND is_active=true")
    pending     = await pool.fetchval("SELECT COUNT(*) FROM providers WHERE is_approved=false AND is_active=true")
    clients     = await pool.fetchval("SELECT COUNT(*) FROM clients")
    searches    = await pool.fetchval("SELECT COUNT(*) FROM searches")
    by_district = await pool.fetch("""
        SELECT d.name, COUNT(p.id) AS cnt
        FROM districts d
        LEFT JOIN providers p ON p.district_id=d.id AND p.is_approved=true AND p.is_active=true
        GROUP BY d.id, d.name ORDER BY d.sort_order
    """)
    return providers, pending, clients, searches, by_district
