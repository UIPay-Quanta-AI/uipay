import { IsEnum, IsNotEmpty, IsString, MaxLength } from 'class-validator';

export enum SupportMessageType {
  CHAT = 'chat',
  ISSUE = 'issue',
}

export class CreateSupportMessageDto {
  @IsEnum(SupportMessageType)
  type!: SupportMessageType;

  @IsString()
  @IsNotEmpty()
  @MaxLength(2000)
  message!: string;
}
