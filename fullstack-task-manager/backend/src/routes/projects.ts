import { Router } from 'express';
import { z } from 'zod';
import { PrismaClient } from '@prisma/client';
import { authenticate, AuthRequest, authorize } from '../middleware/auth';
import { createError } from '../middleware/errorHandler';
import { cache } from '../utils/cache';

const router = Router();
const prisma = new PrismaClient();

const projectSchema = z.object({
  name: z.string().min(1).max(200),
  description: z.string().max(2000).optional(),
  color: z.string().regex(/^#[0-9A-Fa-f]{6}$/).optional()
});

router.use(authenticate);

/**
 * @swagger
 * /projects:
 *   get:
 *     summary: List user's projects
 *     tags: [Projects]
 *     security:
 *       - bearerAuth: []
 *     parameters:
 *       - in: query
 *         name: status
 *         schema:
 *           type: string
 *           enum: [ACTIVE, ARCHIVED]
 */
router.get('/', async (req: AuthRequest, res, next) => {
  try {
    const cacheKey = `projects:${req.user!.id}:${req.query.status || 'all'}`;
    const cached = await cache.get(cacheKey);

    if (cached) {
      res.json(cached);
      return;
    }

    const projects = await prisma.project.findMany({
      where: {
        OR: [
          { ownerId: req.user!.id },
          { members: { some: { userId: req.user!.id } } }
        ],
        status: req.query.status as any || 'ACTIVE'
      },
      include: {
        owner: {
          select: { id: true, firstName: true, lastName: true, email: true }
        },
        members: {
          include: {
            user: {
              select: { id: true, firstName: true, lastName: true, email: true, avatar: true }
            }
          }
        },
        _count: {
          select: { tasks: true }
        }
      },
      orderBy: { updatedAt: 'desc' }
    });

    await cache.set(cacheKey, projects, 300);
    res.json(projects);
  } catch (error) {
    next(error);
  }
});

/**
 * @swagger
 * /projects:
 *   post:
 *     summary: Create a new project
 *     tags: [Projects]
 *     security:
 *       - bearerAuth: []
 */
router.post('/', async (req: AuthRequest, res, next) => {
  try {
    const data = projectSchema.parse(req.body);

    const project = await prisma.project.create({
      data: {
        ...data,
        ownerId: req.user!.id,
        members: {
          create: {
            userId: req.user!.id,
            role: 'OWNER'
          }
        }
      },
      include: {
        owner: {
          select: { id: true, firstName: true, lastName: true }
        },
        members: {
          include: {
            user: {
              select: { id: true, firstName: true, lastName: true }
            }
          }
        }
      }
    });

    await cache.deletePattern(`projects:${req.user!.id}:*`);
    res.status(201).json(project);
  } catch (error) {
    next(error);
  }
});

/**
 * @swagger
 * /projects/{id}:
 *   get:
 *     summary: Get project by ID
 *     tags: [Projects]
 *     security:
 *       - bearerAuth: []
 */
router.get('/:id', async (req: AuthRequest, res, next) => {
  try {
    const project = await prisma.project.findFirst({
      where: {
        id: req.params.id,
        OR: [
          { ownerId: req.user!.id },
          { members: { some: { userId: req.user!.id } } }
        ]
      },
      include: {
        owner: {
          select: { id: true, firstName: true, lastName: true, email: true }
        },
        members: {
          include: {
            user: {
              select: { id: true, firstName: true, lastName: true, email: true, avatar: true }
            }
          }
        },
        tasks: {
          include: {
            assignee: {
              select: { id: true, firstName: true, lastName: true, avatar: true }
            }
          },
          orderBy: { createdAt: 'desc' }
        }
      }
    });

    if (!project) {
      throw createError('Project not found', 404, 'NOT_FOUND');
    }

    res.json(project);
  } catch (error) {
    next(error);
  }
});

export { router as projectRouter };
