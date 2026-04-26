import { MOCK_COMMUNITY_POSTS } from '@/lib/demoData';
import { NextResponse } from 'next/server';

export async function GET() {
  return NextResponse.json(MOCK_COMMUNITY_POSTS);
}
