import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import { Loader2, Plus } from 'lucide-react';

export function ProjectPage() {
  const { id } = useParams<{ id: string }>();

  const { data: project, isLoading } = useQuery({
    queryKey: ['project', id],
    queryFn: async () => {
      const res = await api.get(`/projects/${id}`);
      return res.data;
    },
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex h-96 items-center justify-center">
        <p className="text-gray-500 dark:text-gray-400">Project not found</p>
      </div>
    );
  }

  const taskColumns = [
    { status: 'TODO', label: 'To Do', color: 'bg-gray-100 dark:bg-gray-700' },
    { status: 'IN_PROGRESS', label: 'In Progress', color: 'bg-blue-50 dark:bg-blue-900/20' },
    { status: 'IN_REVIEW', label: 'In Review', color: 'bg-yellow-50 dark:bg-yellow-900/20' },
    { status: 'DONE', label: 'Done', color: 'bg-green-50 dark:bg-green-900/20' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <div
            className="h-10 w-10 rounded-lg"
            style={{ backgroundColor: project.color }}
          />
          <div className="ml-4">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              {project.name}
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              {project.description}
            </p>
          </div>
        </div>
        <button className="btn-primary">
          <Plus className="mr-2 h-4 w-4" />
          New Task
        </button>
      </div>

      {/* Members */}
      <div className="flex items-center space-x-2">
        <span className="text-sm text-gray-600 dark:text-gray-400">Members:</span>
        <div className="flex -space-x-2">
          {project.members?.map((member: any) => (
            <div
              key={member.user.id}
              className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-600 text-xs font-medium text-white ring-2 ring-white dark:ring-gray-800"
              title={`${member.user.firstName} ${member.user.lastName}`}
            >
              {member.user.firstName?.[0]}{member.user.lastName?.[0]}
            </div>
          ))}
        </div>
      </div>

      {/* Kanban Board */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
        {taskColumns.map((column) => (
          <div key={column.status} className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-medium text-gray-900 dark:text-white">
                {column.label}
              </h3>
              <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600 dark:bg-gray-700 dark:text-gray-400">
                {project.tasks?.filter((t: any) => t.status === column.status).length || 0}
              </span>
            </div>
            <div className={`min-h-[200px] rounded-lg ${column.color} p-3 space-y-3`}>
              {project.tasks
                ?.filter((task: any) => task.status === column.status)
                .map((task: any) => (
                  <div
                    key={task.id}
                    className="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800"
                  >
                    <h4 className="font-medium text-gray-900 dark:text-white">
                      {task.title}
                    </h4>
                    {task.assignee && (
                      <div className="mt-2 flex items-center">
                        <div className="h-6 w-6 rounded-full bg-primary-600 flex items-center justify-center text-xs text-white">
                          {task.assignee.firstName?.[0]}
                        </div>
                        <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
                          {task.assignee.firstName} {task.assignee.lastName}
                        </span>
                      </div>
                    )}
                  </div>
                ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
