"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { type AppNotification, getNotifications, markNotificationRead, markAllNotificationsRead } from "@/lib/api";

const TYPE_ICONS: Record<string, string> = {
  review_requested: "\u{1F4CB}",
  approved: "\u2705",
  rejected: "\u274C",
  conflict_detected: "\u26A0\uFE0F",
  comment_added: "\u{1F4AC}",
  enacted: "\u{1F680}",
  reverted: "\u21A9\uFE0F",
};

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [userId, setUserId] = useState("system");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getNotifications(userId);
      setNotifications(data.items);
      setUnreadCount(data.unread_count);
    } catch {
      setNotifications([]);
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => { load(); }, [load]);

  const handleMarkRead = async (id: string) => {
    await markNotificationRead(id);
    await load();
  };

  const handleMarkAllRead = async () => {
    await markAllNotificationsRead(userId);
    await load();
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold" title="Notifications for proposal activity, approval requests, and governance events">Notifications</h1>
          <p className="text-sm text-gray-500 mt-1">
            {unreadCount > 0 ? `${unreadCount} unread` : "All caught up"}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <input
            type="text"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            placeholder="Your user ID"
            className="border rounded-md px-3 py-1.5 text-sm w-32"
          />
          {unreadCount > 0 && (
            <button
              onClick={handleMarkAllRead}
              className="text-sm text-blue-600 hover:text-blue-700"
              title="Mark all notifications as read"
            >
              Mark all read
            </button>
          )}
        </div>
      </div>

      {loading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-gray-100 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : notifications.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <p>No notifications</p>
        </div>
      ) : (
        <div className="space-y-1">
          {notifications.map((n: AppNotification) => (
            <div
              key={n.id}
              className={`flex items-start gap-3 p-3 rounded-lg transition ${
                n.read ? "bg-white" : "bg-blue-50"
              }`}
            >
              <span className="text-lg mt-0.5">
                {TYPE_ICONS[n.notification_type] || "\u{1F514}"}
              </span>
              <div className="flex-1 min-w-0">
                <p className={`text-sm ${n.read ? "text-gray-600" : "text-gray-900 font-medium"}`}>
                  {n.title}
                </p>
                {n.body && (
                  <p className="text-xs text-gray-500 mt-0.5">{n.body}</p>
                )}
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-xs text-gray-400">
                    {new Date(n.created_at).toLocaleString()}
                  </span>
                  {n.proposal_id && (
                    <Link href={`/proposals/${n.proposal_id}`} className="text-xs text-blue-600 hover:underline">
                      View proposal
                    </Link>
                  )}
                </div>
              </div>
              {!n.read && (
                <button
                  onClick={() => handleMarkRead(n.id)}
                  className="text-xs text-gray-400 hover:text-gray-600 shrink-0"
                  title="Mark as read"
                >
                  Mark read
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
