"use client";

import { HugeiconsIcon, type HugeiconsIconProps } from "@hugeicons/react";
import {
  Message01Icon,
  StructureFolderIcon,
  ColorsIcon,
  UserGroupIcon,
  Wallet01Icon,
  Download01Icon,
  Settings01Icon,
  HelpCircleIcon,
  Logout01Icon,
  DashboardSquare01Icon,
  Target01Icon,
  File01Icon,
  Megaphone01Icon,
  CodeIcon,
  Calendar01Icon,
  Image01Icon,
  Film01Icon,
  CheckmarkCircle01Icon,
  ReceiptDollarIcon,
  Shield01Icon,
  SentIcon,
  Loading01Icon,
  SparklesIcon,
  CheckmarkCircle02Icon,
  EyeIcon,
  Attachment01Icon,
  BotIcon,
  Sun01Icon,
  Moon01Icon,
  ComputerSettingsIcon,
  UserIcon,
  Cancel01Icon,
  Add01Icon,
  Clock01Icon,
  ArrowLeft01Icon,
  ArrowRight01Icon,
  ArrowDown01Icon,
  ArrowUp01Icon,
  FolderAddIcon,
  Menu01Icon,
  PanelLeftCloseIcon,
  MenuCollapseIcon,
  ChatFeedback01Icon,
  Mic01Icon,
  StopIcon,
  Delete01Icon,
  Mail01Icon,
  CallIcon,
  Location01Icon,
  GlobeIcon,
  MoreVerticalIcon,
  Archive01Icon,
  AlertCircleIcon,
  RotateLeft01Icon,
  PencilEdit01Icon,
  StarIcon,
  LockIcon,
  Notification01Icon,
  Idea01Icon,
  Search01Icon,
  ShoppingBag01Icon,
} from "@hugeicons/core-free-icons";
import { cn } from "@/lib/utils";

type IconProps = Omit<HugeiconsIconProps, "icon"> & {
  className?: string;
};

function createIcon(icon: HugeiconsIconProps["icon"], displayName?: string) {
  const Component = ({ className, size = 24, ...props }: IconProps) => (
    <HugeiconsIcon
      icon={icon}
      size={size}
      className={cn("shrink-0", className)}
      {...props}
    />
  );
  if (displayName) Component.displayName = displayName;
  return Component;
}

// Application icons (Lucide-compatible names for drop-in replacement)
export const MessageSquare = createIcon(Message01Icon, "MessageSquare");
export const FolderKanban = createIcon(StructureFolderIcon, "FolderKanban");
export const Palette = createIcon(ColorsIcon, "Palette");
export const Users = createIcon(UserGroupIcon, "Users");
export const Wallet = createIcon(Wallet01Icon, "Wallet");
export const Download = createIcon(Download01Icon, "Download");
export const Settings = createIcon(Settings01Icon, "Settings");
export const HelpCircle = createIcon(HelpCircleIcon, "HelpCircle");
export const LogOut = createIcon(Logout01Icon, "LogOut");
export const LayoutDashboard = createIcon(
  DashboardSquare01Icon,
  "LayoutDashboard"
);
export const Target = createIcon(Target01Icon, "Target");
export const FileText = createIcon(File01Icon, "FileText");
export const Megaphone = createIcon(Megaphone01Icon, "Megaphone");
export const FileCode = createIcon(CodeIcon, "FileCode");
export const Calendar = createIcon(Calendar01Icon, "Calendar");
export const Image = createIcon(Image01Icon, "Image");
export const Film = createIcon(Film01Icon, "Film");
export const FileCheck = createIcon(CheckmarkCircle01Icon, "FileCheck");
export const Receipt = createIcon(ReceiptDollarIcon, "Receipt");
export const Shield = createIcon(Shield01Icon, "Shield");
export const Send = createIcon(SentIcon, "Send");
export const Loader2 = createIcon(Loading01Icon, "Loader2");
export const Sparkles = createIcon(SparklesIcon, "Sparkles");
export const Check = createIcon(CheckmarkCircle02Icon, "Check");
export const Eye = createIcon(EyeIcon, "Eye");
export const Paperclip = createIcon(Attachment01Icon, "Paperclip");
export const Bot = createIcon(BotIcon, "Bot");
export const Sun = createIcon(Sun01Icon, "Sun");
export const Moon = createIcon(Moon01Icon, "Moon");
export const Monitor = createIcon(ComputerSettingsIcon, "Monitor");
export const User = createIcon(UserIcon, "User");
export const X = createIcon(Cancel01Icon, "X");
export const Plus = createIcon(Add01Icon, "Plus");
export const Clock = createIcon(Clock01Icon, "Clock");
export const ChevronLeft = createIcon(ArrowLeft01Icon, "ChevronLeft");
export const ChevronRight = createIcon(ArrowRight01Icon, "ChevronRight");
export const ChevronUp = createIcon(ArrowUp01Icon, "ChevronUp");
export const FolderPlus = createIcon(FolderAddIcon, "FolderPlus");
export const GripVertical = createIcon(Menu01Icon, "GripVertical");
export const PanelLeftClose = createIcon(PanelLeftCloseIcon, "PanelLeftClose");
export const MenuCollapse = createIcon(MenuCollapseIcon, "MenuCollapse");
export const Feedback = createIcon(ChatFeedback01Icon, "Feedback");
export const Mic = createIcon(Mic01Icon, "Mic");
export const Stop = createIcon(StopIcon, "Stop");
export const Trash2 = createIcon(Delete01Icon, "Trash2");
export const ChevronDown = createIcon(ArrowDown01Icon, "ChevronDown");
export const Mail = createIcon(Mail01Icon, "Mail");
export const Phone = createIcon(CallIcon, "Phone");
export const MapPin = createIcon(Location01Icon, "MapPin");
export const Globe = createIcon(GlobeIcon, "Globe");
export const MoreVertical = createIcon(MoreVerticalIcon, "MoreVertical");
export const Archive = createIcon(Archive01Icon, "Archive");
export const AlertCircle = createIcon(AlertCircleIcon, "AlertCircle");
export const RotateCcw = createIcon(RotateLeft01Icon, "RotateCcw");
export const Pencil = createIcon(PencilEdit01Icon, "Pencil");
export const Star = createIcon(StarIcon, "Star");
export const Lock = createIcon(LockIcon, "Lock");
export const Bell = createIcon(Notification01Icon, "Bell");
export const Lightbulb = createIcon(Idea01Icon, "Lightbulb");
export const Search = createIcon(Search01Icon, "Search");
export const ShoppingBag = createIcon(ShoppingBag01Icon, "ShoppingBag");
