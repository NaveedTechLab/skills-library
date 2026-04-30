import { Router } from 'express';
import { z } from 'zod';
import { db } from '../db';
import { authenticate } from '../middleware/auth';
import { validate } from '../middleware/validate';

const router = Router();
router.use(authenticate);

// ---- Validation schemas ----
const CreateSchema = z.object({
  name:        z.string().min(1).max(200),
  description: z.string().max(2000).optional(),
  status:      z.enum(['draft', 'active', 'archived']).default('draft'),
});

const UpdateSchema = CreateSchema.partial();

const QuerySchema = z.object({
  page:    z.coerce.number().int().min(1).default(1),
  limit:   z.coerce.number().int().min(1).max(100).default(20),
  status:  z.enum(['draft', 'active', 'archived']).optional(),
  search:  z.string().max(200).optional(),
  sortBy:  z.enum(['name', 'created_at', 'updated_at', 'status']).default('created_at'),
  sortDir: z.enum(['asc', 'desc']).default('desc'),
});

const ALLOWED_SORT = new Set(['name', 'created_at', 'updated_at', 'status']);

// GET /resources
router.get('/', validate('query', QuerySchema), async (req, res, next) => {
  const { page, limit, status, search, sortBy, sortDir } = req.query as z.infer<typeof QuerySchema>;
  const offset = (page - 1) * limit;

  const conditions = ['deleted_at IS NULL', 'user_id = $1'];
  const values: unknown[] = [req.user!.sub];

  if (status) { values.push(status); conditions.push(`status = $${values.length}`); }
  if (search) {
    values.push(`%${search.replace(/[%_]/g, '\\$&')}%`);
    conditions.push(`(name ILIKE $${values.length} OR description ILIKE $${values.length})`);
  }

  const col = ALLOWED_SORT.has(sortBy) ? sortBy : 'created_at';
  const dir = sortDir === 'asc' ? 'ASC' : 'DESC';
  const where = conditions.join(' AND ');

  try {
    const [{ rows: items }, { rows: [{ count }] }] = await Promise.all([
      db.query(`SELECT * FROM resources WHERE ${where} ORDER BY ${col} ${dir} LIMIT $${values.length + 1} OFFSET $${values.length + 2}`, [...values, limit, offset]),
      db.query(`SELECT COUNT(*) FROM resources WHERE ${where}`, values),
    ]);
    res.json({ data: items, meta: { total: parseInt(count), page, limit, pages: Math.ceil(parseInt(count) / limit) } });
  } catch (err) { next(err); }
});

// GET /resources/:id
router.get('/:id', async (req, res, next) => {
  try {
    const { rows: [item] } = await db.query(
      'SELECT * FROM resources WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL',
      [req.params.id, req.user!.sub]
    );
    if (!item) return res.status(404).json({ error: 'NOT_FOUND' });
    res.json({ data: item });
  } catch (err) { next(err); }
});

// POST /resources
router.post('/', validate('body', CreateSchema), async (req, res, next) => {
  try {
    const { rows: [item] } = await db.query(
      'INSERT INTO resources (user_id, name, description, status) VALUES ($1, $2, $3, $4) RETURNING *',
      [req.user!.sub, req.body.name, req.body.description ?? null, req.body.status]
    );
    res.status(201).json({ data: item });
  } catch (err) { next(err); }
});

// PATCH /resources/:id
router.patch('/:id', validate('body', UpdateSchema), async (req, res, next) => {
  const allowed = ['name', 'description', 'status'];
  const fields = Object.keys(req.body).filter(k => allowed.includes(k));
  if (fields.length === 0) return res.status(400).json({ error: 'NO_FIELDS' });

  const sets = fields.map((f, i) => `${f} = $${i + 3}`).join(', ');
  const vals = fields.map(f => req.body[f]);

  try {
    const { rows: [item] } = await db.query(
      `UPDATE resources SET ${sets}, updated_at = NOW() WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL RETURNING *`,
      [req.params.id, req.user!.sub, ...vals]
    );
    if (!item) return res.status(404).json({ error: 'NOT_FOUND' });
    res.json({ data: item });
  } catch (err) { next(err); }
});

// DELETE /resources/:id — SOFT DELETE
router.delete('/:id', async (req, res, next) => {
  try {
    const { rowCount } = await db.query(
      'UPDATE resources SET deleted_at = NOW(), updated_at = NOW() WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL',
      [req.params.id, req.user!.sub]
    );
    if (!rowCount) return res.status(404).json({ error: 'NOT_FOUND' });
    res.status(204).send();
  } catch (err) { next(err); }
});

export { router as resourceRouter };
