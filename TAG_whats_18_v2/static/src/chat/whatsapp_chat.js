/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onWillDestroy, useState, useRef, useEffect } from "@odoo/owl";

export class WhatsappChat extends Component {
    static template = "TAG_whats_18_v2.WhatsappChat";

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.messagesRef = useRef("messagesEnd");
        this.state = useState({
            threads: [],
            activeKey: false,
            activeThread: false,
            messages: [],
            search: "",
            draft: "",
            sending: false,
            loadingThreads: true,
            loadingMessages: false,
        });

        onWillStart(() => this.loadThreads());

        this.pollingId = setInterval(() => this.refresh(), 5000);
        onWillDestroy(() => clearInterval(this.pollingId));

        useEffect(
            () => {
                if (this.messagesRef.el) {
                    this.messagesRef.el.scrollIntoView({ block: "end" });
                }
            },
            () => [this.state.messages.length]
        );
    }

    async loadThreads() {
        this.state.threads = await this.orm.call("adv.whatsapp.out", "get_chat_threads", [this.state.search]);
        this.state.loadingThreads = false;
        if (!this.state.activeKey && this.state.threads.length) {
            this.selectThread(this.state.threads[0]);
        }
    }

    async refresh() {
        await this.loadThreads();
        if (this.state.activeKey) {
            this.state.messages = await this.orm.call("adv.whatsapp.out", "get_chat_messages", [this.state.activeKey]);
        }
    }

    async onSearchInput(ev) {
        this.state.search = ev.target.value;
        await this.loadThreads();
    }

    async selectThread(thread) {
        this.state.activeKey = thread.key;
        this.state.activeThread = thread;
        this.state.loadingMessages = true;
        this.state.messages = await this.orm.call("adv.whatsapp.out", "get_chat_messages", [thread.key]);
        this.state.loadingMessages = false;
        thread.unread = 0;
    }

    onDraftInput(ev) {
        this.state.draft = ev.target.value;
    }

    onKeydown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.sendMessage();
        }
    }

    async sendMessage() {
        const body = this.state.draft.trim();
        if (!body || !this.state.activeKey || this.state.sending) {
            return;
        }
        this.state.sending = true;
        this.state.draft = "";
        try {
            this.state.messages = await this.orm.call("adv.whatsapp.out", "send_chat_message", [
                this.state.activeKey,
                body,
            ]);
            await this.loadThreads();
        } catch (e) {
            this.notification.add(e.message || "Failed to send message", { type: "danger" });
        } finally {
            this.state.sending = false;
        }
    }
}

registry.category("actions").add("whatsapp_chat", WhatsappChat);
