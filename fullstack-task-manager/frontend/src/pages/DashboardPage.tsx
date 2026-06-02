import { useQuery } from '@tanstack/react-query';
import {
  FolderKanban,
  CheckSquare,
  Clock,
  TrendingUp,
  Plus,
} from 'lucide-react';
import { api } from '../services/api';
import { Link } from 'react-router-dom';

interface Stats {
  totalProjects: number;
  totalTasks: number;
  completedTasks: number;
  inProgressTasks: number;
}

export function DashboardPage() {
  const { data: stats } = useQuery<Stats>({
    queryKey: ['dashboard-stats'],
    queryFn: async () => {
      // In a real app, this would be a dedicated endpoint
      const [projectsRes, tasksRes] = await Promise.all([
        api.get('/projects'),
        api.get('/tasks'),
      ]);

      const tasks = tasksRes.data;
      return {
        totalProjects: projectsRes.data.length,
        totalTasks: tasks.length,
        completedTasks: tasks.filter((t: any) => t.status === 'DONE').length,
        inProgressTasks: tasks.filter((t: any) => t.status === 'IN_PROGRESS').length,
      };
    },
  });

  const { data: recentProjects } = useQuery({
    queryKey: ['recent-projects'],
    queryFn: async () => {
      const res = await api.get('/projects?limit=5');
      return res.data.slice(0, 4);
    },
  });

  const statCards = [
    {
      name: 'Total Projects',
      value: stats?.totalProjects || 0,
      icon: FolderKanban,
      color: 'bg-blue-500',
    },
    {
      name: 'Total Tasks',
      value: stats?.totalTasks || 0,
      icon: CheckSquare,
      color: 'bg-green-500',
    },
    {
      name: 'In Progress',
      value: stats?.inProgressTasks || 0,
      icon: Clock,
      color: 'bg-yellow-500',
    },
    {
      name: 'Completed',
      value: stats?.completedTasks || 0,
      icon: TrendingUp,
      color: 'bg-purple-500',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Dashboard
          </h1>
          <p className="mt-1 text-gray-600 dark:text-gray-400">
            Overview of your projects and tasks
          </p>
        </div>
        <button className="btn-primary">
          <Plus className="mr-2 h-4 w-4" />
          New Project
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {statCards.map((stat) => (
          <div key={stat.name} className="card p-6">
            <div className="flex items-center">
              <div className={`rounded-lg ${stat.color} p-3`}>
                <stat.icon className="h-6 w-6 text-white" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  {stat.name}
                </p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {stat.value}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Recent Projects */}
      <div className="card">
        <div className="border-b border-gray-200 px-6 py-4 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Recent Projects
          </h2>
        </div>
        <div className="divide-y divide-gray-200 dark:divide-gray-700">
          {recentProjects?.map((project: any) => (
            <Link
              key={project.id}
              to={`/projects/${project.id}`}
              className="flex items-center px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700/50"
            >
              <div
                className="h-10 w-10 rounded-lg"
                style={{ backgroundColor: project.color }}
              />
              <div className="ml-4 flex-1">
                <h3 className="text-sm font-medium text-gray-900 dark:text-white">
                  {project.name}
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {project._count?.tasks || 0} tasks
                </p>
              </div>
              <div className="text-sm text-gray-500 dark:text-gray-400">
                {project.members?.length || 1} members
              </div>
            </Link>
          ))}
          {(!recentProjects || recentProjects.length === 0) && (
            <div className="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
              No projects yet. Create your first project to get started.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
