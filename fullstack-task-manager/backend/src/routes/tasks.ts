import { Router } from 'express';
import { z } from 'zod';
import { PrismaClient, TaskStatus, Priority } from '@prisma/client';
import { authenticate, AuthRequest } from '../middleware/auth';
import { createError } from '../middleware/errorHandler';

const router = Router();
const prisma = new PrismaClient();

const taskSchema = z.object({
  title: z.string().min(1).max(300),
  description: z.string().max(5000).optional(),
  status: z.nativeEnum(TaskStatus).optional(),
  priority: z.nativeEnum(Priority).optional(),
  dueDate: z.string().datetime().optional().nullable(),
  assigneeId: z.string().uuid().optional().nullable(),
  projectId: z.string().uuid()
});

router.use(authenticate);

/**
 * @swagger
 * /tasks:
 *   get:
 *     summary: List tasks with filters
 *     tags: [Tasks]
 *     security:
 *       - bearerAuth: []
 *     parameters:
 *       - in: query
 *         name: projectId
 *         schema: { type: string }
 *       - in: query
 *         name: status
 *         schema: { type: string }
 *       - in: query
 *         name: assigneeId
 *         schema: { type: string }
 */
router.get('/', async (req: AuthRequest, res, next) => {
  try {
    const where: any = {};

    if (req.query.projectId) {
      where.projectId = req.query.projectId;
    }
    if (req.query.status) {
      where.status = req.query.status;
    }
    if (req.query.assigneeId) {
      where.assigneeId = req.query.assigneeId;
    }
    if (req.query.priority) {
      where.priority = req.query.priority;
    }

    const tasks = await prisma.task.findMany({
      where,
      include: {
        assignee: {
          select: { id: true, firstName: true, lastName: true, avatar: true }
        },
        creator: {
          select: { id: true, firstName: true, lastName: true }
        },
        project: {
          select: { id: true, name: true, color: true }
        },
        _count: {
          select: { comments: true }
        }
      },
      orderBy: [
        { priority: 'desc' },
        { dueDate: 'asc' },
        { createdAt: 'desc' }
      ]
    });

    res.json(tasks);
  } catch (error) {
    next(error);
  }
});

/**
 * @swagger
 * /tasks:
 *   post:
 *     summary: Create a new task
 *     tags: [Tasks]
 *     security:
 *       - bearerAuth: []
 */
router.post('/', async (req: AuthRequest, res, next) => {
  try {
    const data = taskSchema.parse(req.body);

    // Verify user has access to project
    const project = await prisma.project.findFirst({
      where: {
        id: data.projectId,
        OR: [
          { ownerId: req.user!.id },
          { members: { some: { userId: req.user!.id } } }
        ]
      }
    });

    if (!project) {
      throw createError('Project not found or access denied', 404, 'NOT_FOUND');
    }

    const task = await prisma.task.create({
      data: {
        title: data.title,
        description: data.description,
        status: data.status || 'TODO',
        priority: data.priority || 'MEDIUM',
        dueDate: data.dueDate ? new Date(data.dueDate) : null,
        assigneeId: data.assigneeId,
        projectId: data.projectId,
        creatorId: req.user!.id
      },
      include: {
        assignee: {
          select: { id: true, firstName: true, lastName: true, avatar: true }
        },
        project: {
          select: { id: true, name: true }
        }
      }
    });

    // Create activity log
    await prisma.activity.create({
      data: {
        action: 'TASK_CREATED',
        details: { taskTitle: task.title },
        projectId: task.projectId,
        taskId: task.id,
        userId: req.user!.id
      }
    });

    res.status(201).json(task);
  } catch (error) {
    next(error);
  }
});

/**
 * @swagger
 * /tasks/{id}:
 *   patch:
 *     summary: Update task
 *     tags: [Tasks]
 *     security:
 *       - bearerAuth: []
 */
router.patch('/:id', async (req: AuthRequest, res, next) => {
  try {
    const updateSchema = taskSchema.partial();
    const data = updateSchema.parse(req.body);

    const existingTask = await prisma.task.findFirst({
      where: {
        id: req.params.id,
        project: {
          OR: [
            { ownerId: req.user!.id },
            { members: { some: { userId: req.user!.id } } }
          ]
        }
      }
    });

    if (!existingTask) {
      throw createError('Task not found', 404, 'NOT_FOUND');
    }

    const task = await prisma.task.update({
      where: { id: req.params.id },
      data: {
        ...(data.title && { title: data.title }),
        ...(data.description !== undefined && { description: data.description }),
        ...(data.status && { status: data.status }),
        ...(data.priority && { priority: data.priority }),
        ...(data.dueDate !== undefined && { dueDate: data.dueDate ? new Date(data.dueDate) : null }),
        ...(data.assigneeId !== undefined && { assigneeId: data.assigneeId })
      },
      include: {
        assignee: {
          select: { id: true, firstName: true, lastName: true, avatar: true }
        },
        project: {
          select: { id: true, name: true }
        }
      }
    });

    // Log status change if applicable
    if (data.status && data.status !== existingTask.status) {
      await prisma.activity.create({
        data: {
          action: 'TASK_STATUS_CHANGED',
          details: {
            from: existingTask.status,
            to: data.status,
            taskTitle: task.title
          },
          projectId: task.projectId,
          taskId: task.id,
          userId: req.user!.id
        }
      });
    }

    res.json(task);
  } catch (error) {
    next(error);
  }
});

export { router as taskRouter };
