/* Copyright 2026 Iu_yang1. SPDX-License-Identifier: Apache-2.0 */
#define ENABLE_L4S_APP_ABI
#define ENABLE_FEAT_F4HWN_OVERLAY_INFO
#include "../app_api.h"
#ifndef L4S_APP_PAGE
#define L4S_APP_PAGE 0
#endif

__attribute__((section(".text.entry")))
void app_main(const app_api_t *api)
{
    if (!api->l4s_request_page(L4S_APP_PAGE)) {
        api->print_normal("RADIO BUSY",0,127,3);
        api->blit_full();
        api->delay_ms(500);
    }
}
